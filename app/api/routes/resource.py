"""분석 자원 라이프사이클 API — 과제 / 용량 산정 / 자원 대장 / 대시보드 / 회수 현황.

MVP는 admin 게이팅(추후 resource_mgr 역할 분리 가능). 실제 프로비저닝·회수는 인프라팀 수행,
포탈은 기록(System of Record) + 라이프사이클 상태 + 만료 D-14 가시화 담당.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.resource import (
    LEDGER_STATUSES,
    PROJECT_STATUSES,
    AnalysisProject,
    ResourceLedger,
)
from app.repositories.resource_repo import ResourceRepository
from app.schemas.auth import UserRead
from app.schemas.resource import (
    AnalysisProjectCreate,
    AnalysisProjectDetail,
    AnalysisProjectRead,
    AnalysisProjectUpdate,
    CapacityEstimateCreate,
    CapacityEstimateRead,
    LedgerTransition,
    ResourceLedgerCreate,
    ResourceLedgerRead,
    ResourceLedgerUpdate,
)
from app.services.resource_service import ResourceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resource", tags=["resource"], dependencies=[Depends(require_admin)])


# ═══════════════════════════════════════════ Projects ═══════════════════════
@router.get("/projects", response_model=list[AnalysisProjectRead])
def list_projects(status: str | None = Query(default=None), db: Session = Depends(get_db)):
    if status and status not in PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 상태: {status}")
    return [AnalysisProjectRead.model_validate(p) for p in ResourceRepository(db).list_projects(status)]


@router.post("/projects", response_model=AnalysisProjectRead, status_code=201)
def create_project(body: AnalysisProjectCreate, db: Session = Depends(get_db), admin: UserRead = Depends(require_admin)):
    svc = ResourceService(db)
    repo = svc.repo
    code = (body.code or "").strip() or svc.generate_code()
    if repo.get_project_by_code(code):
        raise HTTPException(status_code=409, detail=f"과제 코드 '{code}'가 이미 존재합니다.")

    project = AnalysisProject(
        code=code, name=body.name, purpose=body.purpose,
        period_start=body.period_start, period_end=body.period_end,
        owner=body.owner, member_count=body.member_count, members=body.members,
        data_types=body.data_types, datasets=body.datasets,
        security_review_status=body.security_review_status,
        security_review_date=body.security_review_date,
        itsm_ticket=body.itsm_ticket, status="planning", created_by=admin.username,
    )
    created = repo.create_project(project)
    logger.info("analysis project created: code=%s by=%s", code, admin.username)
    return AnalysisProjectRead.model_validate(created)


@router.get("/projects/{project_id}", response_model=AnalysisProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    svc = ResourceService(db)
    project = svc.repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
    detail = AnalysisProjectDetail.model_validate(project)
    detail.ledgers = [svc.to_ledger_read(l) for l in project.ledgers]
    return detail


@router.put("/projects/{project_id}", response_model=AnalysisProjectRead)
def update_project(project_id: int, body: AnalysisProjectUpdate, db: Session = Depends(get_db)):
    repo = ResourceRepository(db)
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
    if body.status and body.status not in PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 상태: {body.status}")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    repo.save()
    db.refresh(project)
    return AnalysisProjectRead.model_validate(project)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    repo = ResourceRepository(db)
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
    repo.delete_project(project)


# ═══════════════════════════════════════════ Capacity Estimate ══════════════
@router.post("/projects/{project_id}/estimates", response_model=CapacityEstimateRead, status_code=201)
def create_estimate(project_id: int, body: CapacityEstimateCreate, db: Session = Depends(get_db)):
    svc = ResourceService(db)
    if not svc.repo.get_project(project_id):
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
    estimate = svc.build_estimate(project_id, body)
    created = svc.repo.create_estimate(estimate)
    return CapacityEstimateRead.model_validate(created)


@router.delete("/estimates/{estimate_id}", status_code=204)
def delete_estimate(estimate_id: int, db: Session = Depends(get_db)):
    repo = ResourceRepository(db)
    est = repo.get_estimate(estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="산정서를 찾을 수 없습니다.")
    repo.delete_estimate(est)


# ═══════════════════════════════════════════ Resource Ledger ════════════════
@router.post("/projects/{project_id}/ledgers", response_model=ResourceLedgerRead, status_code=201)
def create_ledger(project_id: int, body: ResourceLedgerCreate, db: Session = Depends(get_db), admin: UserRead = Depends(require_admin)):
    svc = ResourceService(db)
    if not svc.repo.get_project(project_id):
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
    ledger = ResourceLedger(project_id=project_id, status="draft", recorded_by=admin.username,
                            **body.model_dump())
    created = svc.repo.create_ledger(ledger)
    return svc.to_ledger_read(created)


@router.put("/ledgers/{ledger_id}", response_model=ResourceLedgerRead)
def update_ledger(ledger_id: int, body: ResourceLedgerUpdate, db: Session = Depends(get_db)):
    svc = ResourceService(db)
    ledger = svc.repo.get_ledger(ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="자원 대장을 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ledger, field, value)
    svc.repo.save()
    db.refresh(ledger)
    return svc.to_ledger_read(ledger)


@router.post("/ledgers/{ledger_id}/transition", response_model=ResourceLedgerRead)
def transition_ledger(ledger_id: int, body: LedgerTransition, db: Session = Depends(get_db), admin: UserRead = Depends(require_admin)):
    svc = ResourceService(db)
    ledger = svc.repo.get_ledger(ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="자원 대장을 찾을 수 없습니다.")
    if body.to_status not in LEDGER_STATUSES:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 상태: {body.to_status}")
    try:
        svc.transition_ledger(
            ledger, body.to_status,
            reclaim_reason=body.reclaim_reason, reclaimed_at=body.reclaimed_at, actor=admin.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    logger.info("ledger %s -> %s by %s", ledger_id, body.to_status, admin.username)
    return svc.to_ledger_read(ledger)


@router.delete("/ledgers/{ledger_id}", status_code=204)
def delete_ledger(ledger_id: int, db: Session = Depends(get_db)):
    repo = ResourceRepository(db)
    ledger = repo.get_ledger(ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="자원 대장을 찾을 수 없습니다.")
    repo.delete_ledger(ledger)


# ═══════════════════════════════════════════ Dashboard / Reclaim ════════════
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """활성/만료임박(D-14)/회수대상 + 용량 합계."""
    return ResourceService(db).dashboard()


@router.get("/reclaim")
def reclaim_view(db: Session = Depends(get_db)):
    """자원 회수 현황 (회수대기/회수완료) — 금융권 비용·자원 통제 근거."""
    return ResourceService(db).reclaim_view()

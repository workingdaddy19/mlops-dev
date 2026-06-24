"""분석 자원 라이프사이클 서비스 — 코드생성 / Peak 산정 / 상태전이 / D-14 분류 / 대시보드."""
import secrets
from datetime import date

from sqlalchemy.orm import Session

from app.models.resource import (
    LEDGER_TRANSITIONS,
    RECLAIM_REASONS,
    AnalysisProject,
    CapacityEstimate,
    CapacityWorksheetStep,
    ResourceLedger,
)
from app.repositories.resource_repo import ResourceRepository
from app.schemas.resource import (
    CapacityEstimateCreate,
    ResourceLedgerRead,
)

EXPIRY_SOON_DAYS = 14


class ResourceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ResourceRepository(db)

    # ── Project ─────────────────────────────────────────────────────────────
    def generate_code(self) -> str:
        for _ in range(5):
            code = f"PRJ-{date.today():%Y%m%d}-{secrets.token_hex(2).upper()}"
            if not self.repo.get_project_by_code(code):
                return code
        return f"PRJ-{date.today():%Y%m%d}-{secrets.token_hex(4).upper()}"

    # ── Capacity Estimate (Peak 산정) ────────────────────────────────────────
    @staticmethod
    def build_estimate(project_id: int, body: CapacityEstimateCreate) -> CapacityEstimate:
        """스텝 누적으로 Peak 메모리/ vCPU 산출. 스텝이 없으면 입력값 사용."""
        est = CapacityEstimate(
            project_id=project_id,
            dataset_summary=body.dataset_summary,
            recommended_node=body.recommended_node,
            basis_note=body.basis_note,
            estimated_by=body.estimated_by,
            derived_peak_memory_gb=body.derived_peak_memory_gb,
            derived_peak_vcpu=body.derived_peak_vcpu,
        )

        if body.steps:
            cum = 0.0
            running: list[float] = []
            for s in body.steps:
                cum += (s.mem_delta_gb or 0.0)
                running.append(round(cum, 3))
            peak_mem = max(running)
            peak_idx = running.index(peak_mem)
            vcpus = [s.vcpu for s in body.steps if s.vcpu is not None]
            peak_vcpu = max(vcpus) if vcpus else None

            for i, s in enumerate(body.steps):
                est.steps.append(CapacityWorksheetStep(
                    step_no=i + 1,
                    operation=s.operation,
                    data_scale=s.data_scale,
                    rationale=s.rationale,
                    vcpu=s.vcpu,
                    mem_delta_gb=s.mem_delta_gb,
                    cumulative_peak_gb=running[i],
                    is_peak=(i == peak_idx),
                ))
            est.derived_peak_memory_gb = peak_mem
            est.derived_peak_vcpu = peak_vcpu
        return est

    # ── Ledger 상태 전이 ─────────────────────────────────────────────────────
    def transition_ledger(
        self, ledger: ResourceLedger, to_status: str, *,
        reclaim_reason: str | None = None, reclaimed_at: date | None = None, actor: str | None = None,
    ) -> ResourceLedger:
        allowed = LEDGER_TRANSITIONS.get(ledger.status, ())
        if to_status not in allowed:
            raise ValueError(f"'{ledger.status}' → '{to_status}' 전이는 허용되지 않습니다. (가능: {', '.join(allowed) or '없음'})")

        if to_status == "reclaimed":
            if reclaim_reason not in RECLAIM_REASONS:
                raise ValueError(f"회수 사유가 필요합니다. (가능: {', '.join(RECLAIM_REASONS)})")
            ledger.reclaim_reason = reclaim_reason
            ledger.reclaimed_at = reclaimed_at or date.today()

        ledger.status = to_status
        if actor:
            ledger.recorded_by = actor
        self.repo.save()
        self.db.refresh(ledger)
        return ledger

    # ── D-14 만료 분류 ───────────────────────────────────────────────────────
    @staticmethod
    def expiry_info(expires_at: date | None, today: date | None = None) -> tuple[int | None, str]:
        if not expires_at:
            return None, "none"
        today = today or date.today()
        days = (expires_at - today).days
        if days < 0:
            return days, "overdue"
        if days <= EXPIRY_SOON_DAYS:
            return days, "soon"
        return days, "ok"

    def to_ledger_read(self, ledger: ResourceLedger) -> ResourceLedgerRead:
        days, state = self.expiry_info(ledger.expires_at)
        read = ResourceLedgerRead.model_validate(ledger)
        read.days_to_expiry = days
        read.expiry_state = state
        return read

    # ── 대시보드 ─────────────────────────────────────────────────────────────
    def dashboard(self) -> dict:
        active = self.repo.list_ledgers_by_statuses(("active",))
        rows = [self.to_ledger_read(l) for l in active]
        expiring = [r for r in rows if r.expiry_state == "soon"]
        overdue = [r for r in rows if r.expiry_state == "overdue"]

        totals = {
            "vcpu": round(sum((l.alloc_vcpu or 0) for l in active), 2),
            "mem_gb": round(sum((l.alloc_mem_gb or 0) for l in active), 2),
            "gpu": sum((l.alloc_gpu or 0) for l in active),
        }
        return {
            "active_count": len(active),
            "expiring_count": len(expiring),
            "overdue_count": len(overdue),
            "capacity_totals": totals,
            "active": [r.model_dump(mode="json") for r in rows],
            "expiring": [r.model_dump(mode="json") for r in expiring],
            "overdue": [r.model_dump(mode="json") for r in overdue],
        }

    def reclaim_view(self) -> dict:
        pending = self.repo.list_ledgers_by_statuses(("reclaim_pending",))
        reclaimed = self.repo.list_ledgers_by_statuses(("reclaimed",))
        return {
            "pending": [self.to_ledger_read(l).model_dump(mode="json") for l in pending],
            "reclaimed": [self.to_ledger_read(l).model_dump(mode="json") for l in reclaimed],
        }

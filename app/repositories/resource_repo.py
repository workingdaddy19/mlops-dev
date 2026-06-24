from sqlalchemy.orm import Session, selectinload

from app.models.resource import (
    AnalysisProject,
    CapacityEstimate,
    ResourceLedger,
)


class ResourceRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Project ─────────────────────────────────────────────────────────────
    def list_projects(self, status: str | None = None) -> list[AnalysisProject]:
        q = self.session.query(AnalysisProject)
        if status:
            q = q.filter(AnalysisProject.status == status)
        return q.order_by(AnalysisProject.id.desc()).all()

    def get_project(self, project_id: int) -> AnalysisProject | None:
        return (
            self.session.query(AnalysisProject)
            .options(
                selectinload(AnalysisProject.estimates).selectinload(CapacityEstimate.steps),
                selectinload(AnalysisProject.ledgers),
            )
            .filter(AnalysisProject.id == project_id)
            .first()
        )

    def get_project_by_code(self, code: str) -> AnalysisProject | None:
        return self.session.query(AnalysisProject).filter(AnalysisProject.code == code).first()

    def create_project(self, project: AnalysisProject) -> AnalysisProject:
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def save(self) -> None:
        self.session.commit()

    def delete_project(self, project: AnalysisProject) -> None:
        self.session.delete(project)
        self.session.commit()

    # ── Capacity Estimate ───────────────────────────────────────────────────
    def create_estimate(self, estimate: CapacityEstimate) -> CapacityEstimate:
        self.session.add(estimate)
        self.session.commit()
        self.session.refresh(estimate)
        return estimate

    def get_estimate(self, estimate_id: int) -> CapacityEstimate | None:
        return self.session.get(CapacityEstimate, estimate_id)

    def delete_estimate(self, estimate: CapacityEstimate) -> None:
        self.session.delete(estimate)
        self.session.commit()

    # ── Resource Ledger ─────────────────────────────────────────────────────
    def get_ledger(self, ledger_id: int) -> ResourceLedger | None:
        return self.session.get(ResourceLedger, ledger_id)

    def create_ledger(self, ledger: ResourceLedger) -> ResourceLedger:
        self.session.add(ledger)
        self.session.commit()
        self.session.refresh(ledger)
        return ledger

    def delete_ledger(self, ledger: ResourceLedger) -> None:
        self.session.delete(ledger)
        self.session.commit()

    def list_ledgers_by_statuses(self, statuses: tuple[str, ...]) -> list[ResourceLedger]:
        return (
            self.session.query(ResourceLedger)
            .filter(ResourceLedger.status.in_(statuses))
            .order_by(ResourceLedger.expires_at.is_(None), ResourceLedger.expires_at.asc())
            .all()
        )

    def list_all_ledgers(self) -> list[ResourceLedger]:
        return self.session.query(ResourceLedger).order_by(ResourceLedger.id.desc()).all()

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.permission_request import PermissionRequest


class PermissionRequestRepository:
    def __init__(self, db: Session):
        self._db = db

    def create(self, req: PermissionRequest) -> PermissionRequest:
        self._db.add(req)
        self._db.commit()
        self._db.refresh(req)
        return req

    def get_by_id(self, req_id: int) -> PermissionRequest | None:
        return self._db.get(PermissionRequest, req_id)

    def delete(self, req: PermissionRequest) -> None:
        self._db.delete(req)
        self._db.commit()

    def list_by_user(self, user_id: int, dt_from: date | None = None, dt_to: date | None = None) -> list[PermissionRequest]:
        q = self._db.query(PermissionRequest).filter(PermissionRequest.user_id == user_id)
        if dt_from:
            q = q.filter(PermissionRequest.requested_at >= dt_from)
        if dt_to:
            q = q.filter(PermissionRequest.requested_at < dt_to + timedelta(days=1))
        return q.order_by(PermissionRequest.id.desc()).all()

    def list_all(self, status: str | None = None, username: str | None = None,
                 dt_from: date | None = None, dt_to: date | None = None) -> list[PermissionRequest]:
        q = self._db.query(PermissionRequest)
        if status:
            q = q.filter(PermissionRequest.status == status)
        if username:
            q = q.filter(PermissionRequest.username.ilike(f"%{username}%"))
        if dt_from:
            q = q.filter(PermissionRequest.requested_at >= dt_from)
        if dt_to:
            q = q.filter(PermissionRequest.requested_at < dt_to + timedelta(days=1))
        return q.order_by(PermissionRequest.id.desc()).all()

    def has_pending(self, user_id: int, feature: str) -> bool:
        return (
            self._db.query(PermissionRequest.id)
            .filter(
                PermissionRequest.user_id == user_id,
                PermissionRequest.feature == feature,
                PermissionRequest.status == "pending",
            )
            .first()
            is not None
        )

    def decide(self, req: PermissionRequest, status: str, decided_by: str) -> PermissionRequest:
        req.status = status
        req.decided_by = decided_by
        req.decided_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(req)
        return req

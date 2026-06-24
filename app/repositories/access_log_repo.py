from datetime import datetime

from sqlalchemy.orm import Session

from app.models.access_log import AccessLog


class AccessLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, log: AccessLog) -> AccessLog:
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_filtered(
        self,
        *,
        username: str | None = None,
        department: str | None = None,
        menu: str | None = None,
        action: str | None = None,
        dt_from: datetime | None = None,
        dt_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AccessLog], int]:
        """필터 조건으로 접속 로그 조회. (행 목록, 전체 건수) 반환."""
        q = self.session.query(AccessLog)
        if username:
            q = q.filter(AccessLog.username.ilike(f"%{username}%"))
        if department:
            q = q.filter(AccessLog.department.ilike(f"%{department}%"))
        if menu:
            q = q.filter(AccessLog.menu.ilike(f"%{menu}%"))
        if action:
            q = q.filter(AccessLog.action == action)
        if dt_from:
            q = q.filter(AccessLog.accessed_at >= dt_from)
        if dt_to:
            q = q.filter(AccessLog.accessed_at < dt_to)

        total = q.count()
        rows = q.order_by(AccessLog.id.desc()).limit(limit).offset(offset).all()
        return rows, total

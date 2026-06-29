from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.query_history import DataQueryHistory


class QueryHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, history: DataQueryHistory) -> DataQueryHistory:
        self.session.add(history)
        self.session.commit()
        self.session.refresh(history)
        return history

    def list_by_user(self, username: str, dt_from: date | None = None, dt_to: date | None = None,
                     limit: int = 200) -> list[DataQueryHistory]:
        q = self.session.query(DataQueryHistory).filter(DataQueryHistory.username == username)
        if dt_from:
            q = q.filter(DataQueryHistory.executed_at >= dt_from)
        if dt_to:
            q = q.filter(DataQueryHistory.executed_at < dt_to + timedelta(days=1))
        return q.order_by(DataQueryHistory.id.desc()).limit(limit).all()

    def list_all(self, dt_from: date | None = None, dt_to: date | None = None,
                 limit: int = 200) -> list[DataQueryHistory]:
        """전체 사용자의 쿼리 기록 (admin 전용)."""
        q = self.session.query(DataQueryHistory)
        if dt_from:
            q = q.filter(DataQueryHistory.executed_at >= dt_from)
        if dt_to:
            q = q.filter(DataQueryHistory.executed_at < dt_to + timedelta(days=1))
        return q.order_by(DataQueryHistory.id.desc()).limit(limit).all()

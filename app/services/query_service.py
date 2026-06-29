from sqlalchemy.orm import Session

from app.repositories.query_history_repo import QueryHistoryRepository
from app.schemas.query import QueryHistoryRead


class QueryService:
    def __init__(self, session: Session, history_repo: QueryHistoryRepository):
        self.session = session
        self.history_repo = history_repo

    def get_history(self, username: str, dt_from=None, dt_to=None) -> list[QueryHistoryRead]:
        items = self.history_repo.list_by_user(username, dt_from, dt_to)
        return [QueryHistoryRead.model_validate(h) for h in items]

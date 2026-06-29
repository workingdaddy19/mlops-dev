from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        return self.session.query(User).filter(User.username == username).first()

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def list_all(self, username: str | None = None, name: str | None = None,
                 dt_from: date | None = None, dt_to: date | None = None) -> list[User]:
        q = self.session.query(User)
        if username:
            q = q.filter(User.username.ilike(f"%{username}%"))
        if name:
            q = q.filter(User.name.ilike(f"%{name}%"))
        if dt_from:
            q = q.filter(User.created_at >= dt_from)
        if dt_to:
            q = q.filter(User.created_at < dt_to + timedelta(days=1))
        return q.order_by(User.id).all()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

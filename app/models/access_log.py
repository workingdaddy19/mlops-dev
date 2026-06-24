from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AccessLog(Base):
    """사용자 접속/메뉴 이용 감사 로그 (금융권 보안).

    값은 조회 편의를 위해 username/name/department를 비정규화 저장한다.
    """

    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    client_ip: Mapped[str | None] = mapped_column(String(64))
    menu: Mapped[str | None] = mapped_column(String(100))
    path: Mapped[str | None] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="view")  # view/login/logout
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

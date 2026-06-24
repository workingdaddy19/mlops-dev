from datetime import datetime

from pydantic import BaseModel


class AccessLogCreate(BaseModel):
    """프론트엔드 비콘 입력 — 현재 페이지 경로 + 동작(view/logout)."""

    path: str
    action: str = "view"


class AccessLogRead(BaseModel):
    id: int
    user_id: int | None = None
    username: str
    name: str | None = None
    department: str | None = None
    client_ip: str | None = None
    menu: str | None = None
    path: str | None = None
    action: str
    accessed_at: datetime | None = None

    class Config:
        from_attributes = True

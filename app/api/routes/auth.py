import logging
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_auth_service, get_current_user, get_db
from app.api.routes.access_log import log_login_event, record_event
from app.core.config import get_settings
from app.core.security import hash_password, validate_password_strength, verify_password
from app.models.user_permission import VALID_FEATURES
from app.repositories.user_permission_repo import UserPermissionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginResponse, UserRead
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    username: str = Form(),
    password: str = Form(),
    service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    logger.info(f"📝 Login attempt: username={username}")
    try:
        result = service.login(username, password)
    except ValueError as e:
        logger.error(f"❌ Login failed: username={username}, error={str(e)}")
        log_login_event(db, request, username, success=False)
        raise HTTPException(status_code=401, detail=str(e)) from e
    logger.info(f"✅ Login success: username={username}")
    log_login_event(db, request, username, success=True)
    return result


@router.get("/me", response_model=UserRead)
def me(current_user: UserRead = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """본인 비밀번호 변경 — 현재 비번 확인 + 정책 검증 후 변경."""
    secret_key = get_settings().secret_key.get_secret_value()
    repo = UserRepository(db)
    user = repo.get_by_id(current_user.id)
    if user is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if not verify_password(body.current_password, user.username, secret_key, user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="새 비밀번호가 기존 비밀번호와 동일합니다.")
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    user.password_hash = hash_password(body.new_password, user.username, secret_key)
    user.must_change_password = False
    db.commit()

    record_event(
        db, request, user_id=user.id, username=user.username,
        name=user.name, department=user.department,
        menu="비밀번호 변경", action="password_change",
    )
    return {"message": "비밀번호가 변경되었습니다."}


@router.get("/me/permissions", response_model=list[str])
def my_permissions(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """현재 로그인 유저의 허용된 기능 목록. admin은 전체 반환."""
    if current_user.role == "admin":
        return sorted(VALID_FEATURES)
    return UserPermissionRepository(db).get_by_user(current_user.id)
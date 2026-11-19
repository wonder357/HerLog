from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_token
from app.core.errors import conflict
from app.db.session import get_session
from app.schemas.auth import CredentialsIn, LoginResult, MemberOut, RegisterResult
from app.schemas.common import ApiResponse
from app.services import auth_service
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/username-register", response_model=ApiResponse[RegisterResult])
def username_register(
    payload: CredentialsIn, session: Session = Depends(get_session)
) -> ApiResponse[RegisterResult]:
    """匿名入口：只有注册和登录不带 require_customer。"""

    try:
        profile = auth_service.register(session, payload.username, payload.password)
    except IntegrityError as exc:
        raise conflict("该用户名已被注册") from exc
    return ApiResponse(data=RegisterResult(username=profile.username))


@router.post("/username-login", response_model=ApiResponse[LoginResult])
def username_login(
    payload: CredentialsIn, session: Session = Depends(get_session)
) -> ApiResponse[LoginResult]:
    result = auth_service.login(session, payload.username, payload.password)
    return ApiResponse(data=LoginResult(**result))


@router.get("/me", response_model=ApiResponse[MemberOut])
def me(
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user)
) -> ApiResponse[MemberOut]:
    return ApiResponse(data=MemberOut(**auth_service.member_view(session, user.customer_id)))


@router.post("/logout", response_model=ApiResponse[None])
def logout(
    session: Session = Depends(get_session), token: str | None = Depends(get_token)
) -> ApiResponse[None]:
    auth_service.logout(session, token)
    return ApiResponse(data=None)

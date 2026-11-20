from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_token
from app.core.config import settings
from app.core.errors import ApiError, conflict
from app.core.security import validate_new_password
from app.db.session import get_session
from app.schemas.auth import (
    AuthOptionsOut, CredentialsIn, LoginResult, MemberOut, PhoneBindingIn, PhoneIn,
    RegisterResult, SmsChallengeOut, SmsProofIn, SmsRequestIn, VerifiedRegisterIn,
)
from app.schemas.common import ApiResponse
from app.services import auth_service, sms_service
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/options", response_model=ApiResponse[AuthOptionsOut])
def auth_options(request: Request):
    mode = sms_service.mode_for(request)
    return ApiResponse(data=AuthOptionsOut(
        sms_mode=mode, requires_phone=settings.HERLOG_SMS_MODE == "aliyun" or mode == "demo",
    ))


@router.post("/sms-code", response_model=ApiResponse[SmsChallengeOut], response_model_exclude_none=True)
def send_code(payload: SmsRequestIn, request: Request):
    return ApiResponse(data=sms_service.issue(request, payload.phone, payload.purpose))


@router.post("/phone-login", response_model=ApiResponse[LoginResult])
def phone_login(payload: SmsProofIn, request: Request, session: Session = Depends(get_session)):
    sms_service.verify(request, payload, "login")
    return ApiResponse(data=LoginResult(**auth_service.login_verified(session, payload.phone)))


@router.post("/phone-register", response_model=ApiResponse[LoginResult])
def phone_register(payload: VerifiedRegisterIn, request: Request, session: Session = Depends(get_session)):
    validate_new_password(payload.password)
    if auth_service.find_member_by_username(session, payload.username):
        raise conflict("该用户名已被注册")
    sms_service.verify(request, payload, "register")
    try:
        result = auth_service.register_verified(session, payload.username, payload.password, payload.phone)
    except IntegrityError as exc:
        raise conflict("用户名或手机号已被使用，请重新检查") from exc
    return ApiResponse(data=LoginResult(**result))


@router.post("/phone-binding/code", response_model=ApiResponse[SmsChallengeOut], response_model_exclude_none=True)
def send_binding_code(
    payload: PhoneIn, request: Request, session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    auth_service.require_unbound_phone(session, user.customer_id)
    return ApiResponse(data=sms_service.issue(request, payload.phone, "bind", user.customer_id))


@router.post("/phone-binding", response_model=ApiResponse[MemberOut])
def bind_phone(
    payload: PhoneBindingIn, request: Request, session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    sms_service.verify(request, payload, "bind", user.customer_id)
    try:
        result = auth_service.bind_verified_phone(session, user.customer_id, payload.password, payload.phone)
    except IntegrityError as exc:
        raise conflict("该手机号已绑定其他账号") from exc
    return ApiResponse(data=MemberOut(**result))


@router.post("/username-register", response_model=ApiResponse[RegisterResult])
def username_register(
    payload: CredentialsIn, session: Session = Depends(get_session)
) -> ApiResponse[RegisterResult]:
    """保留未启用短信的旧环境注册。"""

    if settings.HERLOG_SMS_MODE == "aliyun":
        raise ApiError(403, "请使用手机号验证注册")
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

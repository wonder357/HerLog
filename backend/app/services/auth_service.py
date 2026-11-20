from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import settings
from app.core.errors import ApiError, conflict, unauthorized
from app.core.security import (
    hash_password,
    new_token,
    require_password,
    token_digest,
    verify_password,
)
from app.models.member import MemberAuth, MemberAuthSession
from app.models.herlog import Profile


@dataclass(frozen=True)
class CurrentUser:
    customer_id: str
    username: str
    session_id: str


def register(session: Session, username: str, password: str) -> Profile:
    """用户名注册：会员主体 + 比赛资料同一事务写入，phone 保持 NULL。"""

    profile, _ = _new_member(session, username, password)
    session.commit()
    return profile


def _new_member(
    session: Session, username: str, password: str, verified_phone: str | None = None,
) -> tuple[Profile, MemberAuth]:
    hashed = hash_password(password)
    customer_id = uuid.uuid4().hex
    now = utc_now()
    member = MemberAuth(
        customer_id=customer_id,
        phone=None,
        org_id=None,
        password=hashed,
        status="active",
        created_at=now,
        updated_at=now,
    )
    profile = Profile(customer_id=customer_id, username=username, verified_phone=verified_phone)
    session.add(member)
    session.add(profile)
    return profile, member


def register_verified(session: Session, username: str, password: str, phone: str) -> dict:
    if session.scalar(select(Profile.customer_id).where(Profile.verified_phone == phone)):
        raise conflict("该手机号已用于登录，请直接登录")
    profile, member = _new_member(session, username, password, phone)
    return issue_session(session, profile, member)


def login_verified(session: Session, phone: str) -> dict:
    found = session.execute(
        select(Profile, MemberAuth).join(MemberAuth, Profile.customer_id == MemberAuth.customer_id)
        .where(Profile.verified_phone == phone, MemberAuth.status == "active").with_for_update()
    ).one_or_none()
    if found is None:
        raise unauthorized("该号码暂不可用。新用户可注册，老用户可用账号密码登录")
    return issue_session(session, *found)


def require_unbound_phone(session: Session, customer_id: str, *, lock: bool = False) -> Profile:
    query = select(Profile).where(Profile.customer_id == customer_id)
    profile = session.scalar(query.with_for_update() if lock else query)
    if profile is None:
        raise unauthorized()
    if profile.verified_phone:
        raise conflict("该账号已绑定登录手机号")
    return profile


def bind_verified_phone(session: Session, customer_id: str, password: str, phone: str) -> dict:
    profile = require_unbound_phone(session, customer_id, lock=True)
    member = session.scalar(select(MemberAuth).where(MemberAuth.customer_id == customer_id).with_for_update())
    if not member or member.status != "active" or not verify_password(password, member.password):
        raise ApiError(422, "当前密码不正确或账号暂不可用，请重新获取验证码", {"reason": "sms_consumed"})
    if session.scalar(select(Profile.customer_id).where(Profile.verified_phone == phone)):
        raise conflict("该手机号已绑定其他账号")
    bound = session.execute(
        update(Profile).where(Profile.customer_id == customer_id, Profile.verified_phone.is_(None))
        .values(verified_phone=phone)
    )
    if bound.rowcount != 1:
        raise conflict("该账号已绑定登录手机号")
    session.commit()
    return _member_out(profile, member)


def find_member_by_username(session: Session, username: str) -> tuple[Profile, MemberAuth] | None:
    profile = session.scalar(select(Profile).where(Profile.username == username))
    if profile is None:
        return None
    member = session.scalar(
        select(MemberAuth).where(MemberAuth.customer_id == profile.customer_id)
    )
    if member is None:
        return None
    return profile, member


def login(session: Session, username: str, password: str) -> dict:
    require_password(password)
    found = find_member_by_username(session, username)
    if found is None:
        raise unauthorized("用户名或密码错误")
    profile, member = found
    session.refresh(member, with_for_update=True)
    if not verify_password(password, member.password):
        raise unauthorized("用户名或密码错误")
    if member.status != "active":
        raise unauthorized("账号状态不可用")
    return issue_session(session, profile, member)


def issue_session(session: Session, profile: Profile, member: MemberAuth) -> dict:
    token = new_token()
    now = utc_now()
    expires_at = now + timedelta(hours=settings.SESSION_TTL_HOURS)
    session.add(
        MemberAuthSession(
            customer_id=member.customer_id,
            token_hash=token_digest(token),
            created_at=now,
            expires_at=expires_at,
        )
    )
    session.commit()
    return {
        **_member_out(profile, member),
        "session_id": token,
        "token": token,
        "expires_at": expires_at,
    }


def authenticate(session: Session, token: str | None) -> CurrentUser:
    if not token:
        raise unauthorized()
    digest = token_digest(token)
    row = session.scalar(
        select(MemberAuthSession).where(MemberAuthSession.token_hash == digest)
    )
    if row is None or row.revoked_at is not None:
        raise unauthorized()
    now = utc_now()
    if row.expires_at <= now:
        raise unauthorized()
    member = session.scalar(select(MemberAuth).where(MemberAuth.customer_id == row.customer_id))
    if member is None or member.status != "active":
        raise unauthorized()
    profile = session.scalar(select(Profile).where(Profile.customer_id == row.customer_id))
    if profile is None:
        raise unauthorized()
    row.last_used_at = now
    session.commit()
    return CurrentUser(customer_id=member.customer_id, username=profile.username, session_id=token)


def logout(session: Session, token: str | None) -> None:
    if not token:
        return
    row = session.scalar(
        select(MemberAuthSession).where(MemberAuthSession.token_hash == token_digest(token))
    )
    if row is None or row.revoked_at is not None:
        return
    row.revoked_at = utc_now()
    session.commit()


def member_view(session: Session, customer_id: str) -> dict:
    profile = session.scalar(select(Profile).where(Profile.customer_id == customer_id))
    member = session.scalar(select(MemberAuth).where(MemberAuth.customer_id == customer_id))
    if profile is None or member is None:
        raise unauthorized()
    return _member_out(profile, member)


def _member_out(profile: Profile, member: MemberAuth) -> dict:
    phone = profile.verified_phone
    return {
        "customer_id": member.customer_id,
        "username": profile.username,
        "name": profile.username,
        "phone": member.phone,
        "verified_phone_hint": f"{phone[:3]}****{phone[-4:]}" if phone else None,
        "avatar": None,
        "org_id": None,
        "org_ids": [],
    }

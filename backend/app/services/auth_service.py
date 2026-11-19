from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import settings
from app.core.errors import unauthorized
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
    profile = Profile(customer_id=customer_id, username=username)
    session.add(member)
    session.add(profile)
    # 并发重名由 uq_herlog_username 裁决，IntegrityError 统一映射为 409。
    session.commit()
    return profile


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
        "session_id": token,
        "token": token,
        "customer_id": member.customer_id,
        "username": profile.username,
        "name": profile.username,
        "phone": member.phone,
        "avatar": None,
        "org_id": None,
        "org_ids": [],
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
    return {
        "customer_id": member.customer_id,
        "username": profile.username,
        "name": profile.username,
        "phone": member.phone,
        "avatar": None,
        "org_id": None,
        "org_ids": [],
    }

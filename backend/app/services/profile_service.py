from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import unauthorized
from app.models.herlog import Profile
from app.schemas.herlog import ProfileOut, ProfileUpdate


def get_profile(session: Session, customer_id: str) -> ProfileOut:
    profile = session.scalar(select(Profile).where(Profile.customer_id == customer_id))
    if profile is None:
        raise unauthorized()
    return ProfileOut(
        username=profile.username,
        birthday=profile.birthday,
        height_cm=profile.height_cm,
        contact_phone=profile.contact_phone,
    )


def update_profile(session: Session, customer_id: str, payload: ProfileUpdate) -> ProfileOut:
    profile = session.scalar(select(Profile).where(Profile.customer_id == customer_id))
    if profile is None:
        raise unauthorized()
    # PUT 语义：未提交的字段保持原值，显式 null 表示清空。
    provided = payload.model_fields_set
    if "birthday" in provided:
        profile.birthday = payload.birthday
    if "height_cm" in provided:
        profile.height_cm = payload.height_cm
    if "contact_phone" in provided:
        profile.contact_phone = payload.contact_phone
    session.commit()
    return get_profile(session, customer_id)

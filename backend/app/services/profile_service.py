from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import unauthorized
from app.models.herlog import Profile
from app.models.private_photo import ProfilePhoto
from app.schemas.herlog import ProfileOut, ProfileUpdate
from app.services import private_photo


def get_profile(session: Session, customer_id: str) -> ProfileOut:
    profile = session.scalar(select(Profile).where(Profile.customer_id == customer_id))
    if profile is None:
        raise unauthorized()
    return ProfileOut(
        username=profile.username,
        birthday=profile.birthday,
        height_cm=profile.height_cm,
        contact_phone=profile.contact_phone,
        has_avatar=private_photo.digest_for(session, ProfilePhoto, customer_id) is not None,
    )


def update_profile(session: Session, customer_id: str, payload: ProfileUpdate) -> ProfileOut:
    profile = session.get(Profile, customer_id, with_for_update=True)
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
    if "avatar" in provided:
        private_photo.replace(session, ProfilePhoto, customer_id, private_photo.prepare(payload.avatar, max_side=512))
    session.commit()
    return get_profile(session, customer_id)

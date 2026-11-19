from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO

from fastapi import Response
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import invalid, not_found
from app.models.private_photo import CheckinPhoto, ProfilePhoto, WeightPhoto
from app.schemas.private_photo import PrivatePhotoIn
from app.services.image_validation import decode_image

PhotoModel = type[CheckinPhoto] | type[ProfilePhoto] | type[WeightPhoto]


@dataclass(frozen=True)
class PreparedPhoto:
    data: bytes
    digest: str


def prepare(payload: PrivatePhotoIn | None, *, max_side: int = 1024) -> PreparedPhoto | None:
    if payload is None:
        return None
    decoded = decode_image(payload.image_base64, payload.mime)
    with Image.open(BytesIO(decoded.data)) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        if "A" in image.getbands() or "transparency" in image.info:
            rgba = image.convert("RGBA")
            rgb = Image.new("RGB", rgba.size, "white")
            rgb.paste(rgba, mask=rgba.getchannel("A"))
        else:
            rgb = image.convert("RGB")
        # 新像素缓冲确保 EXIF、ICC、原始文件名等信息不进入存储。
        clean = Image.new("RGB", rgb.size)
        clean.paste(rgb)
        output = BytesIO()
        clean.save(output, "JPEG", quality=85)
    data = output.getvalue()
    if len(data) > settings.SKIN_MAX_UPLOAD_BYTES:
        raise invalid("图片超过 3 MiB，请换一张")
    return PreparedPhoto(data, sha256(data).hexdigest())


def digest_for(session: Session, model: PhotoModel, record_id: int | str) -> str | None:
    return session.scalar(select(model.digest).where(model.record_id == record_id))


def visible_ids(session: Session, model: PhotoModel, record_ids: Sequence[int]) -> set[int]:
    if not record_ids:
        return set()
    return set(session.scalars(select(model.record_id).where(model.record_id.in_(record_ids))))


def replace(session: Session, model: PhotoModel, record_id: int | str, photo: PreparedPhoto | None) -> None:
    """调用方先验证并锁定所属记录。此函数与记录本身共用事务。"""
    row = session.get(model, record_id, with_for_update=True)
    if row is None:
        if photo is not None:
            session.add(model(record_id=record_id, image_bytes=photo.data, digest=photo.digest))
    elif photo is None:
        session.delete(row)
    elif row.digest != photo.digest:
        row.image_bytes = photo.data
        row.digest = photo.digest


def image_response(session: Session, model: PhotoModel, record_id: int | str) -> Response:
    """调用方已按登录账号验证所属记录。二进制走单独接口。"""
    image = session.scalar(select(model.image_bytes).where(model.record_id == record_id))
    if image is None:
        raise not_found()
    return Response(image, media_type="image/jpeg", headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })

from __future__ import annotations

import base64
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import local_day_end_utc, local_day_start_utc, to_utc_naive
from app.core.config import settings
from app.core.errors import ApiError, invalid, not_found
from app.models.herlog import SkinObservation
from app.schemas.herlog import (
    SkinAnalysisOut,
    SkinAnalyzeIn,
    SkinObservationOut,
    SkinQualityOut,
    SkinSummaryOut,
)
from app.services import vision
from app.services.image_validation import decode_image
from app.services.pending_store import PendingStore


def _expires_iso(seconds: int) -> str:
    moment = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return moment.isoformat().replace("+00:00", "Z")


def analyze(
    session: Session, customer_id: str, payload: SkinAnalyzeIn, store: PendingStore
) -> SkinAnalysisOut:
    image = decode_image(payload.image_base64, payload.mime)
    captured_at = to_utc_naive(payload.captured_at)
    observation = vision.observe_skin(image, payload.site)
    analysis_id = uuid.uuid4().hex
    expires_at = _expires_iso(settings.PENDING_TTL_SECONDS)
    store.put(
        customer_id,
        analysis_id,
        {
            "site": payload.site,
            "captured_at": captured_at.isoformat(),
            "mime": image.mime,
            "image_base64": base64.b64encode(image.data).decode("ascii"),
            "visible": observation.visible,
            "unclear": observation.unclear,
            "attention": observation.attention,
            "model_id": observation.model_id,
            "prompt_version": observation.prompt_version,
        },
        settings.PENDING_TTL_SECONDS,
    )
    return SkinAnalysisOut(
        analysis_id=analysis_id,
        expires_at=expires_at,
        site=payload.site,
        captured_at=captured_at.isoformat() + "Z",
        quality=SkinQualityOut(level=observation.quality, message=observation.quality_message),
        visible=observation.visible,
        unclear=observation.unclear,
        attention=observation.attention,
        model_id=observation.model_id,
        prompt_version=observation.prompt_version,
        demo_sample=observation.demo_sample,
    )


def _to_out(row: SkinObservation) -> SkinObservationOut:
    return SkinObservationOut(
        id=row.id,
        site=row.site,
        captured_at=row.captured_at.isoformat() + "Z",
        mime=row.mime,
        visible=row.visible,
        unclear=row.unclear,
        attention=row.attention,
        model_id=row.model_id,
        prompt_version=row.prompt_version,
    )


def _find_saved(session: Session, customer_id: str, analysis_id: str) -> SkinObservation | None:
    return session.scalar(
        select(SkinObservation).where(
            SkinObservation.customer_id == customer_id,
            SkinObservation.analysis_id == analysis_id,
        )
    )


def save_observation(
    session: Session, customer_id: str, analysis_id: str, store: PendingStore
) -> tuple[SkinObservationOut, bool]:
    """先查已保存结果再校验暂存：重复保存返回同一条，过期暂存返回 410。"""

    saved = _find_saved(session, customer_id, analysis_id)
    if saved is not None:
        return _to_out(saved), False
    pending = store.get(customer_id, analysis_id)
    if pending is None:
        raise ApiError(410, "分析结果已过期，请重新拍摄")
    row = SkinObservation(
        customer_id=customer_id,
        analysis_id=analysis_id,
        site=pending["site"],
        captured_at=datetime.fromisoformat(pending["captured_at"]),
        mime=pending["mime"],
        image_bytes=base64.b64decode(pending["image_base64"]),
        visible=pending["visible"],
        unclear=pending["unclear"],
        attention=pending["attention"],
        model_id=pending["model_id"],
        prompt_version=pending["prompt_version"],
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # 并发撞唯一键：回滚当前事务并回读本账号已存记录。
        session.rollback()
        existing = _find_saved(session, customer_id, analysis_id)
        if existing is None:
            raise
        return _to_out(existing), False
    store.delete(customer_id, analysis_id)
    return _to_out(row), True


def list_observations(
    session: Session,
    customer_id: str,
    site: str | None = None,
    day_from: date | None = None,
    day_to: date | None = None,
) -> list[SkinSummaryOut]:
    conditions = [SkinObservation.customer_id == customer_id]
    if site:
        conditions.append(SkinObservation.site == site)
    if day_from is not None:
        conditions.append(SkinObservation.captured_at >= local_day_start_utc(day_from))
    if day_to is not None:
        conditions.append(SkinObservation.captured_at < local_day_end_utc(day_to))
    rows = session.scalars(
        select(SkinObservation)
        .where(*conditions)
        .order_by(SkinObservation.captured_at.desc(), SkinObservation.id.desc())
    ).all()
    return [
        SkinSummaryOut(id=row.id, site=row.site, captured_at=row.captured_at.isoformat() + "Z", visible=row.visible)
        for row in rows
    ]


def get_observation(session: Session, customer_id: str, observation_id: int) -> SkinObservationOut:
    row = session.scalar(
        select(SkinObservation).where(
            SkinObservation.id == observation_id, SkinObservation.customer_id == customer_id
        )
    )
    if row is None:
        raise not_found()
    return _to_out(row)


def load_image(session: Session, customer_id: str, observation_id: int) -> tuple[bytes, str]:
    row = session.scalar(
        select(SkinObservation).where(
            SkinObservation.id == observation_id, SkinObservation.customer_id == customer_id
        )
    )
    if row is None:
        raise not_found()
    return row.image_bytes, row.mime


def discard_pending(customer_id: str, analysis_id: str, store: PendingStore) -> None:
    if not analysis_id:
        raise invalid("analysis_id 不能为空")
    store.delete(customer_id, analysis_id)


def latest_observation(session: Session, customer_id: str) -> SkinObservation | None:
    return session.scalar(
        select(SkinObservation)
        .where(SkinObservation.customer_id == customer_id)
        .order_by(SkinObservation.captured_at.desc(), SkinObservation.id.desc())
        .limit(1)
    )

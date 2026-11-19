from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import local_day_end_utc, local_day_start_utc, local_today, to_utc_naive
from app.core.errors import conflict, invalid, not_found
from app.logic import weight as weight_logic
from app.models.herlog import Weight
from app.schemas.herlog import (
    WeightIn,
    WeightListOut,
    WeightOut,
    WeightPointOut,
    WeightSummaryOut,
    weight_out,
)


def _rows(rows: list[Weight]) -> list[weight_logic.WeightRow]:
    return [
        weight_logic.WeightRow(
            id=row.id,
            grams=row.grams,
            measured_at=row.measured_at,
            tag=row.tag,
            note=row.note,
        )
        for row in rows
    ]


def list_weights(
    session: Session,
    customer_id: str,
    day_from: date | None = None,
    day_to: date | None = None,
    tag: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> WeightListOut:
    conditions = [Weight.customer_id == customer_id]
    if day_from is not None:
        conditions.append(Weight.measured_at >= local_day_start_utc(day_from))
    if day_to is not None:
        conditions.append(Weight.measured_at < local_day_end_utc(day_to))
    if tag:
        conditions.append(Weight.tag == tag)
    total = session.scalar(select(func.count()).select_from(Weight).where(*conditions)) or 0
    rows = session.scalars(
        select(Weight)
        .where(*conditions)
        .order_by(Weight.measured_at.desc(), Weight.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return WeightListOut(
        items=[weight_out(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _same_content(row: Weight, payload: WeightIn, measured_at_utc: datetime, grams: int) -> bool:
    return (
        row.grams == grams
        and row.measured_at == measured_at_utc
        and (row.tag or None) == (payload.tag or None)
        and (row.note or None) == (payload.note or None)
    )


def create_weight(session: Session, customer_id: str, payload: WeightIn) -> tuple[WeightOut, bool]:
    """同账号同 client_key 幂等：内容一致返回原记录，内容不同 409。"""

    measured_at_utc = to_utc_naive(payload.measured_at)
    try:
        grams = weight_logic.parse_kg(payload.kg)
    except ValueError as exc:
        raise invalid(str(exc)) from exc
    existing = session.scalar(
        select(Weight).where(Weight.customer_id == customer_id, Weight.client_key == payload.client_key)
    )
    if existing is not None:
        if _same_content(existing, payload, measured_at_utc, grams):
            return weight_out(existing), False
        raise conflict("该请求已用于另一笔体重记录，请刷新后重试")
    row = Weight(
        customer_id=customer_id,
        client_key=payload.client_key,
        grams=grams,
        measured_at=measured_at_utc,
        tag=payload.tag,
        note=payload.note,
    )
    session.add(row)
    session.commit()
    return weight_out(row), True


def update_weight(session: Session, customer_id: str, weight_id: int, payload: WeightIn) -> WeightOut:
    row = session.scalar(
        select(Weight).where(Weight.id == weight_id, Weight.customer_id == customer_id)
    )
    if row is None:
        raise not_found()
    try:
        grams = weight_logic.parse_kg(payload.kg)
    except ValueError as exc:
        raise invalid(str(exc)) from exc
    row.grams = grams
    row.measured_at = to_utc_naive(payload.measured_at)
    row.tag = payload.tag
    row.note = payload.note
    session.commit()
    return weight_out(row)


def delete_weight(session: Session, customer_id: str, weight_id: int) -> None:
    row = session.scalar(
        select(Weight).where(Weight.id == weight_id, Weight.customer_id == customer_id)
    )
    if row is None:
        raise not_found()
    session.delete(row)
    session.commit()


def summary(session: Session, customer_id: str, days: int) -> WeightSummaryOut:
    if days not in (7, 30):
        raise invalid("days 只支持 7 或 30")
    today = local_today()
    start_day = weight_logic.range_start(days, today)
    rows = list(
        session.scalars(
            select(Weight).where(
                Weight.customer_id == customer_id,
                Weight.measured_at >= local_day_start_utc(start_day),
                Weight.measured_at < local_day_end_utc(today),
            )
        ).all()
    )
    latest = session.scalar(
        select(Weight)
        .where(Weight.customer_id == customer_id)
        .order_by(Weight.measured_at.desc(), Weight.id.desc())
        .limit(1)
    )
    if latest is not None and all(row.id != latest.id for row in rows):
        rows.append(latest)
    data = weight_logic.summarize(_rows(rows), days, today)
    return WeightSummaryOut(
        days=days,
        latest_grams=data.latest_grams,
        latest_kg=None if data.latest_grams is None else round(data.latest_grams / 1000, 3),
        latest_measured_at=None
        if data.latest_measured_at is None
        else data.latest_measured_at.isoformat() + "Z",
        count=data.count,
        points=[
            WeightPointOut(
                day=point.day,
                grams=point.grams,
                kg=round(point.grams / 1000, 3),
                weight_id=point.weight_id,
                measured_at=point.measured_at.isoformat() + "Z",
            )
            for point in data.points
        ],
        delta_grams=data.delta_grams,
        delta_kg=data.delta_kg,
        suggestion=weight_logic.suggestion(data),
    )

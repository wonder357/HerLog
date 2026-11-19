from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import local_day_end_utc, local_day_start_utc, local_today, to_local, to_utc_naive
from app.core.errors import conflict, invalid, not_found
from app.logic import weight as weight_logic
from app.models.herlog import Feeling, Profile, Weight
from app.schemas.herlog import (
    WeightIn,
    WeightListOut,
    WeightOut,
    WeightPointOut,
    WeightSummaryOut,
    MetricSlot,
    weight_out,
)
from app.schemas.weight_plus import CompareOut, CompareWindowOut
from app.logic.metabolism import bmi_value
from app.services.cycle_context import cycle_records, phase_for

DEVICE_METRIC_UNITS = {
    "body_fat_pct": "percent",
    "skeletal_muscle_kg": "kg",
    "muscle_mass_kg": "kg",
    "body_water_pct": "percent",
    "bone_mass_kg": "kg",
    "bmr_kcal_per_day": "kcal/day",
    "visceral_fat_level": "vendor_level",
    "protein_pct": "percent",
    "metabolic_age_years": "years",
}


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
        and (row.feeling_tags or []) == list(dict.fromkeys(payload.feeling_tags or []))
    )


def create_weight(session: Session, customer_id: str, payload: WeightIn) -> tuple[WeightOut, bool]:
    """同账号同 client_key 幂等：内容一致返回原记录，内容不同 409。"""

    measured_at_utc = to_utc_naive(payload.measured_at)
    measured_at_utc = measured_at_utc.replace(microsecond=measured_at_utc.microsecond // 1000 * 1000)
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
        feeling_tags=list(dict.fromkeys(payload.feeling_tags or [])),
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(Weight).where(Weight.customer_id == customer_id, Weight.client_key == payload.client_key)
        )
        if existing is None:
            raise
        if not _same_content(existing, payload, measured_at_utc, grams):
            raise conflict("该请求已用于另一笔体重记录，请刷新后重试")
        return weight_out(existing), False
    return weight_out(row), True


def owned_weight(session: Session, customer_id: str, weight_id: int) -> Weight:
    row = session.scalar(
        select(Weight).where(Weight.id == weight_id, Weight.customer_id == customer_id)
    )
    if row is None:
        raise not_found()
    return row


def update_weight(session: Session, customer_id: str, weight_id: int, payload: WeightIn) -> WeightOut:
    row = owned_weight(session, customer_id, weight_id)
    try:
        grams = weight_logic.parse_kg(payload.kg)
    except ValueError as exc:
        raise invalid(str(exc)) from exc
    row.grams = grams
    row.measured_at = to_utc_naive(payload.measured_at)
    row.tag = payload.tag
    row.note = payload.note
    if payload.feeling_tags is not None:
        row.feeling_tags = list(dict.fromkeys(payload.feeling_tags))
    session.commit()
    return weight_out(row)


def delete_weight(session: Session, customer_id: str, weight_id: int) -> None:
    row = owned_weight(session, customer_id, weight_id)
    session.delete(row)
    session.commit()


def summary(session: Session, customer_id: str, days: int, include_cycle: bool = False) -> WeightSummaryOut:
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
    profile = session.get(Profile, customer_id)
    height = profile.height_cm if profile else None
    bmi = bmi_value(latest.grams, height) if latest else None
    metrics = {
        "bmi": MetricSlot(
            value=bmi,
            unit="kg/m2",
            status="available" if bmi is not None else "missing_height" if latest and not height else "no_data",
            source="profile_calculated" if bmi is not None else None,
            measured_at=latest.measured_at.isoformat() + "Z" if bmi is not None and latest else None,
        ),
        **{
            key: MetricSlot(unit=unit, status="not_connected")
            for key, unit in DEVICE_METRIC_UNITS.items()
        },
    }
    cycle_context = None
    if include_cycle:
        periods = cycle_records(session, customer_id)
        feelings = {
            row.day: row.symptoms for row in session.scalars(
                select(Feeling).where(Feeling.customer_id == customer_id, Feeling.day.between(start_day, today))
            )
        }
        flagged_days = {
            to_local(row.measured_at).date()
            for row in rows
            if set(row.feeling_tags or []) & {"bloating", "puffy"}
        }
        cycle_context = []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            context = phase_for(day, periods, today)
            if context.phase == "luteal" and (day in flagged_days or "腹胀" in (feelings.get(day) or [])):
                context.note = "这天处于估算的黄体期。你记录了身体感受，可以和当天的记录一起回看。"
            cycle_context.append(context)
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
        latest_record_id=latest.id if latest else None,
        record_days=len(data.points),
        metrics=metrics,
        cycle_context=cycle_context,
    )


def _window(session: Session, customer_id: str, start_day: date, end_day: date, days: int) -> CompareWindowOut:
    rows = list(
        session.scalars(
            select(Weight).where(
                Weight.customer_id == customer_id,
                Weight.measured_at >= local_day_start_utc(start_day),
                Weight.measured_at < local_day_end_utc(end_day),
            )
        ).all()
    )
    points = weight_logic.daily_points(_rows(rows))
    grams = [point.grams for point in points]
    return CompareWindowOut(
        start_day=start_day,
        end_day=end_day,
        days=days,
        count=len(rows),
        coverage_days=len(points),
        first_kg=None if not grams else round(grams[0] / 1000, 3),
        last_kg=None if not grams else round(grams[-1] / 1000, 3),
        avg_kg=None if not grams else round(sum(grams) / len(grams) / 1000, 3),
        delta_kg=None if len(grams) < 2 else round((grams[-1] - grams[0]) / 1000, 3),
    )


def compare(session: Session, customer_id: str, days: int) -> CompareOut:
    """同一长度前后两段对比：上周 vs 上上周，或近 30 天 vs 前 30 天。"""

    if days not in (7, 30):
        raise invalid("days 只支持 7 或 30")
    today = local_today()
    current_start = weight_logic.range_start(days, today)
    previous_end = current_start - timedelta(days=1)
    previous_start = weight_logic.range_start(days, previous_end)
    current = _window(session, customer_id, current_start, today, days)
    previous = _window(session, customer_id, previous_start, previous_end, days)
    avg_delta = (
        None
        if current.coverage_days < 2 or previous.coverage_days < 2
        else round(current.avg_kg - previous.avg_kg, 3)
    )
    if previous.coverage_days == 0:
        message = f"上一个 {days} 天没有记录，先攒一段同长度的数据再对比。"
    elif current.coverage_days == 0:
        message = f"最近 {days} 天没有记录，暂时无法对比。"
    elif avg_delta is None:
        message = "两段都有记录，但数据点不足，先按天记录再比较。"
    else:
        trend = "低" if avg_delta < 0 else ("高" if avg_delta > 0 else "持平")
        message = (
            f"最近 {days} 天日均 {current.avg_kg} kg，上一个 {days} 天日均 {previous.avg_kg} kg，"
            f"日均{trend} {abs(avg_delta)} kg。"
        )
    return CompareOut(
        days=days,
        current=current,
        previous=previous,
        avg_delta_kg=avg_delta,
        message=message,
    )

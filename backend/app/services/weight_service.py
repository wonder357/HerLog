from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import local_day_end_utc, local_day_start_utc, local_today, to_local, to_utc_naive
from app.core.errors import conflict, invalid, not_found
from app.logic import weight as weight_logic
from app.models.herlog import Feeling, Profile, Weight
from app.models.private_photo import WeightPhoto
from app.schemas.herlog import (
    WeightIn,
    WeightListOut,
    WeightOut,
    WeightPointOut,
    WeightSummaryOut,
    MetricSlot,
    MetricPointOut,
    MetricTrendOut,
    WeightCycleCompareOut,
    WeightCycleOut,
    WeightCyclePointOut,
    WeightCycleSeriesOut,
    weight_out,
)
from app.schemas.weight_plus import CompareOut, CompareWindowOut
from app.logic.metabolism import bmi_value
from app.services.cycle_context import cycle_records, phase_for
from app.services import private_photo

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
    photo_ids = private_photo.visible_ids(session, WeightPhoto, [row.id for row in rows])
    return WeightListOut(
        items=[weight_out(row, row.id in photo_ids) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _same_content(row: Weight, payload: WeightIn, measured_at_utc: datetime, grams: int) -> bool:
    return (
        row.grams == grams
        and row.body_fat_pct == payload.body_fat_pct
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
    photo = private_photo.prepare(payload.photo)

    def existing_response(existing: Weight) -> tuple[WeightOut, bool]:
        digest = private_photo.digest_for(session, WeightPhoto, existing.id)
        if _same_content(existing, payload, measured_at_utc, grams) and digest == (photo.digest if photo else None):
            return weight_out(existing, digest is not None), False
        raise conflict("该请求已用于另一笔体重记录，请刷新后重试")

    existing = session.scalar(
        select(Weight).where(Weight.customer_id == customer_id, Weight.client_key == payload.client_key)
    )
    if existing is not None:
        return existing_response(existing)
    row = Weight(
        customer_id=customer_id,
        client_key=payload.client_key,
        grams=grams,
        body_fat_pct=payload.body_fat_pct,
        measured_at=measured_at_utc,
        tag=payload.tag,
        note=payload.note,
        feeling_tags=list(dict.fromkeys(payload.feeling_tags or [])),
    )
    session.add(row)
    try:
        if photo is not None:
            session.flush()
            private_photo.replace(session, WeightPhoto, row.id, photo)
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(Weight).where(Weight.customer_id == customer_id, Weight.client_key == payload.client_key)
        )
        if existing is None:
            raise
        return existing_response(existing)
    return weight_out(row, photo is not None), True


def owned_weight(session: Session, customer_id: str, weight_id: int, *, lock: bool = False) -> Weight:
    query = select(Weight).where(Weight.id == weight_id, Weight.customer_id == customer_id)
    row = session.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise not_found()
    return row


def update_weight(session: Session, customer_id: str, weight_id: int, payload: WeightIn) -> WeightOut:
    row = owned_weight(session, customer_id, weight_id, lock=True)
    try:
        grams = weight_logic.parse_kg(payload.kg)
    except ValueError as exc:
        raise invalid(str(exc)) from exc
    row.grams = grams
    if "body_fat_pct" in payload.model_fields_set:
        row.body_fat_pct = payload.body_fat_pct
    row.measured_at = to_utc_naive(payload.measured_at)
    row.tag = payload.tag
    row.note = payload.note
    if payload.feeling_tags is not None:
        row.feeling_tags = list(dict.fromkeys(payload.feeling_tags))
    if "photo" in payload.model_fields_set:
        private_photo.replace(session, WeightPhoto, row.id, private_photo.prepare(payload.photo))
    session.commit()
    return weight_out(row, private_photo.digest_for(session, WeightPhoto, row.id) is not None)


def delete_weight(session: Session, customer_id: str, weight_id: int) -> None:
    row = owned_weight(session, customer_id, weight_id, lock=True)
    private_photo.replace(session, WeightPhoto, row.id, None)
    session.flush()
    session.delete(row)
    session.commit()


def _fat_points(rows: list[Weight]) -> list[MetricPointOut]:
    measurements = {row.id: row.body_fat_pct for row in rows if row.body_fat_pct is not None}
    points = weight_logic.daily_points(_rows([row for row in rows if row.id in measurements]))
    return [
        MetricPointOut(day=point.day, value=measurements[point.weight_id], weight_id=point.weight_id,
                       measured_at=point.measured_at.isoformat() + "Z")
        for point in points
    ]


def _trend(points: list[MetricPointOut], digits: int) -> MetricTrendOut:
    delta = round(points[-1].value - points[0].value, digits) if len(points) >= 2 else None
    return MetricTrendOut(points=points, delta=delta)


def _window_rows(session: Session, customer_id: str, start_day: date, end_day: date) -> list[Weight]:
    return list(session.scalars(select(Weight).where(
        Weight.customer_id == customer_id,
        Weight.measured_at >= local_day_start_utc(start_day),
        Weight.measured_at < local_day_end_utc(end_day),
    )))


def summary(session: Session, customer_id: str, days: int, include_cycle: bool = False) -> WeightSummaryOut:
    if days not in (7, 30):
        raise invalid("days 只支持 7 或 30")
    today = local_today()
    start_day = weight_logic.range_start(days, today)
    rows = _window_rows(session, customer_id, start_day, today)
    fat_points = _fat_points(rows)
    latest = session.scalar(
        select(Weight)
        .where(Weight.customer_id == customer_id, Weight.measured_at < local_day_end_utc(today))
        .order_by(Weight.measured_at.desc(), Weight.id.desc())
        .limit(1)
    )
    if latest is not None and all(row.id != latest.id for row in rows):
        rows.append(latest)
    data = weight_logic.summarize(_rows(rows), days, today)
    latest_fat = session.scalar(
        select(Weight).where(Weight.customer_id == customer_id, Weight.body_fat_pct.is_not(None),
                             Weight.measured_at < local_day_end_utc(today))
        .order_by(Weight.measured_at.desc(), Weight.id.desc()).limit(1)
    )
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
            for key, unit in DEVICE_METRIC_UNITS.items() if key != "body_fat_pct"
        },
        "body_fat_pct": MetricSlot(
            value=latest_fat.body_fat_pct if latest_fat else None,
            unit="percent",
            status="available" if latest_fat else "no_data",
            source=latest_fat.source if latest_fat else None,
            measured_at=latest_fat.measured_at.isoformat() + "Z" if latest_fat else None,
        ),
    }
    bmi_points = [
        MetricPointOut(day=point.day, value=value, weight_id=point.weight_id,
                       measured_at=point.measured_at.isoformat() + "Z")
        for point in data.points if (value := bmi_value(point.grams, height)) is not None
    ]
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
        metric_trends={"bmi": _trend(bmi_points, 1), "body_fat_pct": _trend(fat_points, 2)},
        cycle_context=cycle_context,
    )


def _window(session: Session, customer_id: str, start_day: date, end_day: date, days: int) -> CompareWindowOut:
    rows = _window_rows(session, customer_id, start_day, end_day)
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


def cycle_compare(
    session: Session, customer_id: str, current_start: date | None, previous_start: date | None,
) -> WeightCycleCompareOut:
    """Compare only elapsed days measured in two cycles anchored to actual start dates."""

    today = local_today()
    records = [row for row in cycle_records(session, customer_id) if row.start_day <= today]
    cycles = [
        WeightCycleOut(
            start_day=row.start_day,
            end_day=records[index + 1].start_day - timedelta(days=1) if index + 1 < len(records) else today,
            completed=index + 1 < len(records),
        )
        for index, row in enumerate(records)
    ][-8:][::-1]
    if (current_start is None) != (previous_start is None):
        raise invalid("请选择两个周期的实际开始日")
    if current_start is not None and previous_start is not None:
        by_start = {cycle.start_day: cycle for cycle in cycles}
        if current_start not in by_start or previous_start not in by_start:
            raise not_found("没有找到可比较的周期")
        if current_start <= previous_start:
            raise invalid("当前周期须晚于对照周期")
        current, previous = by_start[current_start], by_start[previous_start]
    elif len(cycles) < 2:
        return WeightCycleCompareOut(cycles=cycles)
    else:
        current, previous = cycles[:2]
    aligned = min((cycle.end_day - cycle.start_day).days + 1 for cycle in (current, previous))
    profile = session.get(Profile, customer_id)
    height = profile.height_cm if profile else None

    def series(cycle: WeightCycleOut) -> WeightCycleSeriesOut:
        through = cycle.start_day + timedelta(days=aligned - 1)
        rows = _window_rows(session, customer_id, cycle.start_day, through)
        fat_by_day = {point.day: point.value for point in _fat_points(rows)}
        points = []
        for point in weight_logic.daily_points(_rows(rows)):
            phase = phase_for(point.day, records, today)
            points.append(WeightCyclePointOut(
                day=point.day, phase=phase.phase, basis=phase.basis,
                cycle_day=(point.day - cycle.start_day).days + 1,
                weight_kg=point.grams / 1000, bmi=bmi_value(point.grams, height),
                body_fat_pct=fat_by_day.get(point.day),
            ))
        return WeightCycleSeriesOut(cycle=cycle, points=points)

    return WeightCycleCompareOut(cycles=cycles, current=series(current), previous=series(previous), aligned_days=aligned)

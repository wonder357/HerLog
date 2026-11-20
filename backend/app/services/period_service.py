from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import local_today
from app.core.errors import conflict, not_found
from app.logic import period as period_logic
from app.models.herlog import Period
from app.models.member import MemberAuth
from app.schemas.herlog import PeriodIn, PeriodOut


def lock_member(session: Session, customer_id: str) -> None:
    """区间检查与写入必须在同一会员行锁内完成，防止并发插入两段重叠经期。"""

    session.execute(
        select(MemberAuth.customer_id)
        .where(MemberAuth.customer_id == customer_id)
        .with_for_update()
    ).first()


def _occupied(row: Period) -> tuple[date, date]:
    # 结束未知时，这段经期只占用已知开始日。
    end = row.end_day or row.start_day
    return row.start_day, end


def _assert_no_conflict(
    session: Session, customer_id: str, start_day: date, end_day: date | None, exclude_id: int | None
) -> None:
    new_start, new_end = start_day, end_day or start_day
    existing = session.scalars(select(Period).where(Period.customer_id == customer_id)).all()
    for row in existing:
        if exclude_id is not None and row.id == exclude_id:
            continue
        row_start, row_end = _occupied(row)
        if new_start <= row_end and row_start <= new_end:
            raise conflict(
                f"与已记录的经期（开始 {row_start.isoformat()}）重叠，请检查日期"
            )


def _to_out(row: Period, history: dict[int, dict]) -> PeriodOut:
    extra = history.get(row.id, {})
    return PeriodOut(
        id=row.id,
        start_day=row.start_day,
        end_day=row.end_day,
        duration_days=extra.get("duration_days"),
        cycle_days=extra.get("cycle_days"),
    )


def load_periods(session: Session, customer_id: str) -> list[Period]:
    return list(
        session.scalars(
            select(Period)
            .where(Period.customer_id == customer_id)
            .order_by(Period.start_day.desc(), Period.id.desc())
        ).all()
    )


def list_periods(session: Session, customer_id: str) -> dict:
    rows = load_periods(session, customer_id)
    history = period_logic.build_history([(row.id, row.start_day, row.end_day) for row in rows])
    by_id = {item["id"]: item for item in history}
    today = local_today()
    starts = [row.start_day for row in rows if row.start_day <= today]
    prediction = period_logic.predict_next_start(starts, today)
    expected = prediction.expected_start
    expected_end = None
    ovulatory_window = None
    latest = next((row for row in rows if row.start_day <= today), None)
    if expected:
        expected_end = period_logic.estimate_period_end(expected, (
            item["duration_days"] for item in history
            if item["end_day"] is not None and item["end_day"] <= today
        ))
    if expected and latest and latest.end_day:
        start, end = period_logic.ovulatory_window(expected)
        if start > latest.end_day:
            ovulatory_window = {"start_day": start, "end_day": end, "estimated_day": start + timedelta(days=2)}
    return {
        "items": [_to_out(row, by_id) for row in rows],
        "prediction": {
            "status": prediction.status,
            "expected_start": expected,
            "expected_end": expected_end,
            "estimate_days": prediction.estimate_days,
            "cycle_count": prediction.cycle_count,
            "starts_used": prediction.starts_used,
            "ovulatory_window": ovulatory_window,
            "message": prediction.message,
        },
        "status": _current_status(rows, today, prediction.status == period_logic.OVERDUE),
    }


def _current_status(rows: list[Period], today: date, overdue: bool) -> dict:
    latest = next((row for row in rows if row.start_day <= today), None)
    if latest is not None:
        active = latest.end_day >= today if latest.end_day is not None else not overdue
        if active:
            day_index = (today - latest.start_day).days + 1
            return {
                "in_period": True,
                "day_index": day_index,
                "message": f"经期第 {day_index} 天",
                "start_day": latest.start_day,
                "end_day": latest.end_day,
            }
        if latest.end_day is not None:
            return {
                "in_period": False,
                "day_index": None,
                "message": f"最近一次经期开始 {latest.start_day.isoformat()}",
                "start_day": latest.start_day,
                "end_day": latest.end_day,
            }
        return {
            "in_period": False,
            "day_index": None,
            "message": f"最近一次经期开始 {latest.start_day.isoformat()}，未记录结束",
            "start_day": latest.start_day,
            "end_day": None,
        }
    return {"in_period": False, "day_index": None, "message": "还没有经期记录", "start_day": None, "end_day": None}


def create_period(session: Session, customer_id: str, payload: PeriodIn) -> PeriodOut:
    lock_member(session, customer_id)
    _assert_no_conflict(session, customer_id, payload.start_day, payload.end_day, None)
    row = Period(customer_id=customer_id, start_day=payload.start_day, end_day=payload.end_day)
    session.add(row)
    session.commit()
    rows = load_periods(session, customer_id)
    history = period_logic.build_history([(item.id, item.start_day, item.end_day) for item in rows])
    return _to_out(row, {item["id"]: item for item in history})


def update_period(session: Session, customer_id: str, period_id: int, payload: PeriodIn) -> PeriodOut:
    lock_member(session, customer_id)
    row = session.scalar(
        select(Period).where(Period.id == period_id, Period.customer_id == customer_id)
    )
    if row is None:
        raise not_found()
    _assert_no_conflict(session, customer_id, payload.start_day, payload.end_day, period_id)
    row.start_day = payload.start_day
    row.end_day = payload.end_day
    session.commit()
    rows = load_periods(session, customer_id)
    history = period_logic.build_history([(item.id, item.start_day, item.end_day) for item in rows])
    return _to_out(row, {item["id"]: item for item in history})


def delete_period(session: Session, customer_id: str, period_id: int) -> None:
    lock_member(session, customer_id)
    row = session.scalar(
        select(Period).where(Period.id == period_id, Period.customer_id == customer_id)
    )
    if row is None:
        raise not_found()
    session.delete(row)
    session.commit()

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import local_today
from app.logic import period as period_logic
from app.models.herlog import Period
from app.schemas.herlog import CycleDayOut


def cycle_records(session: Session, customer_id: str) -> list[Period]:
    return list(session.scalars(
        select(Period).where(Period.customer_id == customer_id).order_by(Period.start_day)
    ))


def phase_for(day: date, records: list[Period], today: date) -> CycleDayOut:
    """阶段与月历的排卵日、易孕期共用同一套窗口，避免两处口径不一致。

    - 月经期：已记录的实际区间
    - 易孕期（ovulatory）：排卵日前 5 天到排卵日后 1 天
    - 易孕期之前为卵泡期，之后为黄体期
    """

    previous = [row for row in records if row.start_day <= day]
    unknown = CycleDayOut(day=day, phase="unknown", basis="unknown")
    if not previous or day > today:
        return unknown
    last = previous[-1]
    if day <= (last.end_day or last.start_day):
        return CycleDayOut(day=day, phase="menstrual", basis="recorded")
    if not last.end_day:
        return unknown

    next_start = next((row.start_day for row in records if day < row.start_day <= today), None)
    if next_start is None:
        prediction = period_logic.predict_next_start([row.start_day for row in previous], today)
        if prediction.status not in (period_logic.UPCOMING, period_logic.OVERDUE):
            return unknown
        next_start = prediction.expected_start
    if next_start is None:
        return unknown

    fertile_start, fertile_end = period_logic.fertile_window(next_start)
    if day < fertile_start:
        return CycleDayOut(day=day, phase="follicular", basis="estimated")
    if day <= fertile_end:
        return CycleDayOut(day=day, phase="ovulatory", basis="estimated")
    return CycleDayOut(day=day, phase="luteal", basis="estimated")


def current_phase(session: Session, customer_id: str, day: date) -> CycleDayOut:
    return phase_for(day, cycle_records(session, customer_id), local_today())

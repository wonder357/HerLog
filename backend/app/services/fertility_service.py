from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, select, update
from sqlalchemy.orm import Session

from app.core.clock import local_today, to_utc_naive, utc_now
from app.core.config import settings
from app.core.errors import conflict, invalid, not_found
from app.models.fertility import CyclePreference, FertilityDaily, FertilityTest
from app.schemas.fertility import CycleMode, DailyIn, DailyOut, LHTest, PreferenceOut
from app.services.period_service import lock_member


def _preference_out(row: CyclePreference | None) -> PreferenceOut:
    if row is None:
        return PreferenceOut()
    return PreferenceOut(
        active_mode=row.active_mode, configured=True,
        seen_fertility=row.seen_fertility, trying_started_on=row.trying_started_on,
    )


def get_preference(session: Session, customer_id: str) -> PreferenceOut:
    return _preference_out(session.get(CyclePreference, customer_id))


def _edit_preference(session: Session, customer_id: str) -> CyclePreference:
    lock_member(session, customer_id)
    row = session.get(CyclePreference, customer_id, with_for_update=True)
    if row is None:
        row = CyclePreference(customer_id=customer_id, active_mode="period", seen_fertility=False)
        session.add(row)
    return row


def set_mode(session: Session, customer_id: str, mode: CycleMode) -> PreferenceOut:
    row = _edit_preference(session, customer_id)
    row.active_mode = mode
    if mode == "trying_to_conceive":
        row.seen_fertility = True
    session.commit()
    return _preference_out(row)


def set_start_date(session: Session, customer_id: str, day: date | None) -> PreferenceOut:
    if day is not None and day > local_today():
        raise invalid("备孕开始日期不能晚于今天")
    row = _edit_preference(session, customer_id)
    row.trying_started_on = day
    session.commit()
    return _preference_out(row)


def _with_utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None else None


def _daily_out(row: FertilityDaily, tests: list[LHTest]) -> DailyOut:
    return DailyOut(
        day=row.day, bbt_c=row.bbt_c, bbt_measured_at=_with_utc(row.bbt_measured_at),
        lh_tests=tests, cervical_mucus=row.cervical_mucus,
        intercourse_occurred=row.intercourse_occurred, revision=row.revision, updated_at=_with_utc(row.updated_at),
    )


def list_daily(session: Session, customer_id: str, day_from: date, day_to: date) -> list[DailyOut]:
    if not 0 <= (day_to - day_from).days < 92:
        raise invalid("请选择不超过 92 天的有效日期范围")
    rows = session.execute(
        select(FertilityDaily, FertilityTest).outerjoin(FertilityTest, and_(
            FertilityDaily.customer_id == FertilityTest.customer_id, FertilityDaily.day == FertilityTest.day,
        )).where(FertilityDaily.customer_id == customer_id, FertilityDaily.day.between(day_from, day_to))
        .order_by(FertilityDaily.day, FertilityTest.measured_at.is_(None), FertilityTest.measured_at, FertilityTest.id)
    )
    by_day: dict[date, tuple[FertilityDaily, list[LHTest]]] = {}
    for row, test in rows:
        _, tests = by_day.setdefault(row.day, (row, []))
        if test is not None:
            tests.append(LHTest(result=test.result, measured_at=_with_utc(test.measured_at)))
    return [_daily_out(row, tests) for row, tests in by_day.values()]


def get_daily(session: Session, customer_id: str, day: date) -> DailyOut:
    rows = list_daily(session, customer_id, day, day)
    if not rows:
        raise not_found()
    return rows[0]


def _check_time(value: datetime | None, day: date, now: datetime) -> datetime | None:
    if value is None:
        return None
    result = to_utc_naive(value)
    if value.astimezone(settings.tz).date() != day or result > now:
        raise invalid("测量时间须属于所选日期，且不能晚于当前时间")
    if value.second or value.microsecond:
        raise invalid("测量时间只需精确到分钟")
    return result


def save_daily(session: Session, customer_id: str, day: date, payload: DailyIn) -> DailyOut:
    if day > local_today():
        raise invalid("观察日期不能晚于今天")
    now = utc_now()
    now = now.replace(microsecond=now.microsecond // 1000 * 1000)
    measured_at = _check_time(payload.bbt_measured_at, day, now)
    tests = [(test.result, _check_time(test.measured_at, day, now)) for test in payload.lh_tests]
    lock_member(session, customer_id)
    row = session.get(FertilityDaily, (customer_id, day), with_for_update=True)
    expected = str(payload.expected_revision) if payload.expected_revision else None
    message = "这一天的记录已更新，请比较已保存的内容后重试"
    if row is None and expected is not None:
        raise not_found()
    if (row.revision if row else None) != expected:
        raise conflict(message)
    values = dict(bbt_c=payload.bbt_c, bbt_measured_at=measured_at, cervical_mucus=payload.cervical_mucus,
                  intercourse_occurred=payload.intercourse_occurred, revision=str(uuid4()), updated_at=now)
    if row is None:
        row = FertilityDaily(customer_id=customer_id, day=day, **values)
        session.add(row)
        session.flush()
    else:
        result = session.execute(update(FertilityDaily).where(
            FertilityDaily.customer_id == customer_id, FertilityDaily.day == day, FertilityDaily.revision == expected,
        ).values(**values))
        if result.rowcount != 1:
            raise conflict(message)
        _delete_tests(session, customer_id, day)
    session.add_all(FertilityTest(customer_id=customer_id, day=day, result=result, measured_at=time)
                    for result, time in tests)
    ordered = sorted(tests, key=lambda test: (test[1] is None, test[1]))
    output = _daily_out(row, [LHTest(result=result, measured_at=_with_utc(time)) for result, time in ordered])
    session.commit()
    return output


def _delete_tests(session: Session, customer_id: str, day: date) -> None:
    session.execute(delete(FertilityTest).where(FertilityTest.customer_id == customer_id, FertilityTest.day == day))


def delete_daily(session: Session, customer_id: str, day: date, expected_revision: UUID) -> None:
    lock_member(session, customer_id)
    row = session.get(FertilityDaily, (customer_id, day), with_for_update=True)
    if row is None:
        raise not_found()
    if row.revision != str(expected_revision):
        raise conflict("这一天的记录已更新，请重新查看后再删除")
    _delete_tests(session, customer_id, day)
    result = session.execute(delete(FertilityDaily).where(
        FertilityDaily.customer_id == customer_id, FertilityDaily.day == day,
        FertilityDaily.revision == str(expected_revision),
    ))
    if result.rowcount != 1:
        raise conflict("这一天的记录已更新，请重新查看后再删除")
    session.commit()

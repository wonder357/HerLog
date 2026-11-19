from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from time import time

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.clock import local_day_start_utc, local_today, to_local, utc_now
from app.core.errors import ApiError, invalid, unauthorized
from app.core.security import hash_password, verify_password
from app.logic.period import predict_next_start
from app.models.fertility import CyclePreference
from app.models.herlog import Feeling, Period, Profile, SkinObservation, Weight
from app.models.home import HomePreference
from app.models.member import MemberAuth, MemberAuthSession
from app.models.private_photo import ProfilePhoto
from app.services import private_photo
from app.services.cycle_context import phase_for
from app.services.period_service import lock_member


def _kg(grams: int) -> str:
    return format(Decimal(grams).scaleb(-3).normalize(), "f")


def health_summary(session: Session, customer_id: str) -> dict:
    profile = session.get(Profile, customer_id)
    if profile is None:
        raise unauthorized()
    weight = session.execute(
        select(Weight.grams, Weight.measured_at).where(Weight.customer_id == customer_id, Weight.measured_at <= utc_now())
        .order_by(Weight.measured_at.desc(), Weight.id.desc()).limit(1)
    ).first()
    period_start = session.scalar(
        select(Period.start_day).where(Period.customer_id == customer_id, Period.start_day <= local_today())
        .order_by(Period.start_day.desc()).limit(1)
    )
    captured_at = session.scalar(
        select(SkinObservation.captured_at).where(SkinObservation.customer_id == customer_id, SkinObservation.captured_at <= utc_now())
        .order_by(SkinObservation.captured_at.desc()).limit(1)
    )
    height = profile.height_cm
    weight_day = to_local(weight.measured_at).date() if weight else None
    bmi = None
    if height and weight:
        bmi = (Decimal(weight.grams) * 10 / height**2).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    status = "available" if bmi is not None else "missing_both" if not height and not weight else "missing_height" if not height else "missing_weight"
    return {
        "has_avatar": private_photo.digest_for(session, ProfilePhoto, customer_id) is not None,
        "bmi": {"value": str(bmi) if bmi is not None else None, "status": status,
                "height_cm": str(height) if height else None, "weight_day": weight_day},
        "latest_period_start": period_start, "latest_weight_day": weight_day,
        "latest_skin_observation_day": to_local(captured_at).date() if captured_at else None,
    }


def _day_records(session: Session, customer_id: str, first: date, last: date) -> dict[date, dict]:
    records: dict[date, dict] = {}
    if first > last:
        return records

    def day_record(day: date) -> dict:
        return records.setdefault(day, {"day": day, "weight_kg": None, "skin_observation_count": 0, "feeling_tags": []})

    start = local_day_start_utc(first)
    stop = local_day_start_utc(last + timedelta(days=1))
    now = utc_now()
    weights = session.execute(select(Weight.measured_at, Weight.grams).where(
        Weight.customer_id == customer_id, Weight.measured_at >= start, Weight.measured_at < stop, Weight.measured_at <= now,
    ).order_by(Weight.measured_at.desc(), Weight.id.desc()))
    for measured_at, grams in weights:
        record = day_record(to_local(measured_at).date())
        if record["weight_kg"] is None:
            record["weight_kg"] = _kg(grams)
    photos = session.scalars(select(SkinObservation.captured_at).where(
        SkinObservation.customer_id == customer_id, SkinObservation.captured_at >= start, SkinObservation.captured_at < stop,
        SkinObservation.captured_at <= now,
    ))
    for captured_at in photos:
        day_record(to_local(captured_at).date())["skin_observation_count"] += 1

    feelings = session.execute(select(Feeling.day, Feeling.flow, Feeling.mood, Feeling.symptoms, Feeling.impact).where(
        Feeling.customer_id == customer_id, Feeling.day.between(first, last),
    ))
    for day, flow, mood, symptoms, impact in feelings:
        tags = [tag for tag in [f"经量 {flow}" if flow else None, mood, *(symptoms or []), impact] if tag]
        day_record(day)["feeling_tags"] = tags or ["有感受记录"]
    return records


def _periods_in_range(session: Session, customer_id: str, first: date, last: date) -> list[Period]:
    return list(session.scalars(select(Period).where(
        Period.customer_id == customer_id, Period.start_day <= last,
        or_(Period.start_day >= first, Period.end_day >= first),
    ).order_by(Period.start_day.desc())))


def _recorded_period_days(periods: list[Period], first: date, last: date) -> set[date]:
    return {day for row in periods for day in (row.start_day, row.end_day) if day is not None and first <= day <= last}


def _focus(phase: str, mode: str, has_periods: bool, recorded: bool, birthday: date | None, today: date) -> dict:
    if recorded:
        return {"message_key": "review_today", "action": "review_today"}
    if mode == "trying_to_conceive":
        return {"message_key": "review_periods", "action": "open_period"}
    if phase == "ovulatory" or (phase == "unknown" and has_periods):
        return {"message_key": "review_month", "action": "open_calendar"}
    if not has_periods:
        return {"message_key": "record_period", "action": "record_period"}
    if birthday:
        age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        if age < 18:
            return {"message_key": "record_feeling_simple", "action": "record_feeling"}
    return {"message_key": "record_feeling", "action": "record_feeling"}


def overview(session: Session, customer_id: str, month: str) -> dict:
    try:
        year, number = map(int, month.split("-"))
        if not 1900 <= year <= 9998:
            raise ValueError
        first = date(year, number, 1)
    except ValueError:
        raise invalid("请选择有效月份")
    today = local_today()
    last = date(year, number, monthrange(year, number)[1])
    week_first = today - timedelta(days=today.weekday())
    active_mode = session.scalar(select(CyclePreference.active_mode).where(CyclePreference.customer_id == customer_id)) or "period"
    recent = list(session.scalars(select(Period).where(
        Period.customer_id == customer_id, Period.start_day <= today,
    ).order_by(Period.start_day.desc()).limit(4)))
    prediction = predict_next_start([row.start_day for row in recent], today)
    phase = phase_for(today, list(reversed(recent)), today)
    monthly = _day_records(session, customer_id, first, min(last, today))
    periods = _periods_in_range(session, customer_id, first, min(last, today)) if first <= today else []
    if first <= week_first and today <= last:
        weekly = {day: row for day, row in monthly.items() if day >= week_first}
        week_periods = periods
    else:
        weekly = _day_records(session, customer_id, week_first, today)
        week_periods = _periods_in_range(session, customer_id, week_first, today)
    period_days = _recorded_period_days(week_periods, week_first, today)
    recorded_days = set(weekly) | period_days
    birthday = session.scalar(select(Profile.birthday).where(Profile.customer_id == customer_id))
    latest = recent[0] if recent else None
    today_record = weekly.get(today)
    return {
        "month": month, "timezone": "Asia/Shanghai", "today": today, "active_mode": active_mode,
        "cycle_context": phase, "period_prediction": {"status": prediction.status,
            "expected_start": prediction.expected_start if prediction.status == "upcoming" else None},
        "period_intervals": [{"start_day": row.start_day, "end_day": row.end_day} for row in periods],
        "open_period": {"id": latest.id, "start_day": latest.start_day} if latest and latest.end_day is None else None,
        "days": [monthly[day] for day in sorted(monthly)],
        "week": {"from": week_first, "to": today, "recorded_days": len(recorded_days),
                 "days": sorted(recorded_days), "has_weight": any(row["weight_kg"] is not None for row in weekly.values()),
                 "has_skin": any(row["skin_observation_count"] for row in weekly.values())},
        "today_recorded": {"period": today in period_days, "weight": bool(today_record and today_record["weight_kg"] is not None),
                           "skin": bool(today_record and today_record["skin_observation_count"]),
                           "feeling": bool(today_record and today_record["feeling_tags"])},
        "has_period_history": bool(recent),
        "focus": _focus(phase.phase, active_mode, bool(recent), today in recorded_days, birthday, today),
    }


def preference_view(row: HomePreference | None, fields: dict) -> dict:
    if row is None:
        return fields
    return {key: getattr(row, key) for key in fields}


def update_preferences(session: Session, customer_id: str, values: dict) -> HomePreference:
    lock_member(session, customer_id)
    row = session.get(HomePreference, customer_id, with_for_update=True)
    if row is None:
        row = HomePreference(customer_id=customer_id)
        session.add(row)
    for key, value in values.items():
        setattr(row, key, value)
    session.commit()
    return row


def change_password(session: Session, customer_id: str, current: str, new: str) -> None:
    lock_member(session, customer_id)
    member = session.scalar(select(MemberAuth).where(MemberAuth.customer_id == customer_id).with_for_update())
    if member is None:
        raise unauthorized()
    state = session.get(HomePreference, customer_id, with_for_update=True)
    if state is None:
        state = HomePreference(customer_id=customer_id, password_attempt_count=0)
        session.add(state)
    now = int(time())
    if state.password_attempt_window is None or now - state.password_attempt_window >= 600:
        state.password_attempt_window = now
        state.password_attempt_count = 0
    if state.password_attempt_count >= 5:
        raise ApiError(429, "尝试次数较多，请稍后重试")
    if not verify_password(current, member.password):
        state.password_attempt_count += 1
        session.commit()
        raise invalid("当前密码不正确")
    if current == new:
        raise invalid("新密码需与当前密码不同")
    member.password = hash_password(new)
    member.updated_at = utc_now()
    state.password_attempt_count = 0
    state.password_attempt_window = None
    session.execute(update(MemberAuthSession).where(
        MemberAuthSession.customer_id == customer_id, MemberAuthSession.revoked_at.is_(None),
    ).values(revoked_at=utc_now()))
    session.commit()

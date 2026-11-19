"""体重目标：起点、目标、安全的周速度、进度与按趋势预测达成日。"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import local_today, utc_now
from app.core.errors import invalid
from app.logic import metabolism, weight as weight_logic
from app.models.herlog import Profile, Weight, WeightGoal
from app.schemas.weight_plus import BmiOut, GoalIn, GoalOut


def _profile(session: Session, customer_id: str) -> Profile | None:
    return session.get(Profile, customer_id)


def _height(session: Session, customer_id: str):
    profile = _profile(session, customer_id)
    return None if profile is None else profile.height_cm


def _birthday(session: Session, customer_id: str) -> date | None:
    profile = _profile(session, customer_id)
    return None if profile is None else profile.birthday


def _recent_rows(session: Session, customer_id: str) -> list[Weight]:
    rows = session.scalars(
        select(Weight)
        .where(Weight.customer_id == customer_id)
        .order_by(Weight.measured_at.desc(), Weight.id.desc())
        .limit(400)
    ).all()
    return list(rows)


def _day_points(rows: list[Weight]) -> list[tuple[date, int]]:
    mapped = [
        weight_logic.WeightRow(id=row.id, grams=row.grams, measured_at=row.measured_at)
        for row in rows
    ]
    return [(point.day, point.grams) for point in weight_logic.daily_points(mapped)]


def latest_grams(session: Session, customer_id: str) -> int | None:
    row = session.scalar(
        select(Weight)
        .where(Weight.customer_id == customer_id)
        .order_by(Weight.measured_at.desc(), Weight.id.desc())
        .limit(1)
    )
    return None if row is None else row.grams


def energy_plan(session: Session, customer_id: str) -> tuple[int | None, int | None, int | None]:
    """返回（基础代谢、总消耗、每日摄入目标）；缺身高或生日时为 None，不猜数。"""

    grams = latest_grams(session, customer_id)
    if grams is None:
        return None, None, None
    today = local_today()
    age = metabolism.age_of(_birthday(session, customer_id), today)
    bmr = metabolism.bmr_kcal(grams, _height(session, customer_id), age)
    tdee = metabolism.tdee_kcal(bmr)
    return bmr, tdee, metabolism.intake_target_kcal(tdee, bmr)


def intake_target(session: Session, customer_id: str) -> int | None:
    return energy_plan(session, customer_id)[2]


def bmi_out(session: Session, customer_id: str, grams: int | None) -> BmiOut:
    if grams is None:
        return BmiOut(value=None, category="未知", advice=metabolism.bmi_advice(None))
    value = metabolism.bmi_value(grams, _height(session, customer_id))
    return BmiOut(
        value=value,
        category=metabolism.bmi_category(value),
        advice=metabolism.bmi_advice(value),
    )


def goal_state(session: Session, customer_id: str) -> GoalOut:
    grams = latest_grams(session, customer_id)
    bmr, tdee, target_kcal = energy_plan(session, customer_id)
    bmi = bmi_out(session, customer_id, grams)
    goal = session.get(WeightGoal, customer_id)
    if goal is None:
        return GoalOut(
            has_goal=False,
            bmi=bmi,
            bmr_kcal=bmr,
            tdee_kcal=tdee,
            intake_target_kcal=target_kcal,
            message="设一个目标体重，就能看到进度和按记录的预测日期。",
        )

    points = _day_points(_recent_rows(session, customer_id))
    progress = metabolism.goal_progress(goal.start_grams, goal.target_grams, grams)
    slope = metabolism.slope_grams_per_day(points) if points else None
    forecast = metabolism.forecast_day(points, goal.target_grams) if points else None
    return GoalOut(
        has_goal=True,
        target_kg=round(goal.target_grams / 1000, 3),
        start_kg=round(goal.start_grams / 1000, 3),
        start_day=goal.start_day.isoformat(),
        weekly_rate_kg=round(goal.weekly_rate_grams / 1000, 3),
        percent=progress.percent,
        remaining_kg=round(progress.remaining_grams / 1000, 3),
        reached=progress.reached,
        message=progress.message,
        forecast_day=None if forecast is None else forecast.isoformat(),
        slope_kg_per_week=None if slope is None else round(slope * 7 / 1000, 3),
        bmr_kcal=bmr,
        tdee_kcal=tdee,
        intake_target_kcal=target_kcal,
        bmi=bmi,
    )


def set_goal(session: Session, customer_id: str, payload: GoalIn) -> GoalOut:
    today = local_today()
    grams = latest_grams(session, customer_id)
    if grams is None:
        raise invalid("先记一次体重，再设目标体重")
    target_grams = int(round(float(payload.target_kg) * 1000))
    rate_grams = int(round(float(payload.weekly_rate_kg) * 1000))
    bmi = metabolism.bmi_value(grams, _height(session, customer_id))
    if payload.target_kg * 1000 >= grams:
        raise invalid("目标体重需要低于当前体重；想维持体重可以不改目标")
    if bmi is not None and bmi < metabolism.BMI_LOW:
        raise invalid("BMI 已低于 18.5，不建议继续减重")

    goal = session.get(WeightGoal, customer_id)
    if goal is None:
        goal = WeightGoal(
            customer_id=customer_id,
            target_grams=target_grams,
            start_grams=grams,
            start_day=today,
            weekly_rate_grams=metabolism.clamp_rate_grams(rate_grams, bmi),
            created_at=utc_now(),
        )
        session.add(goal)
    else:
        goal.target_grams = target_grams
        goal.weekly_rate_grams = metabolism.clamp_rate_grams(rate_grams, bmi)
    session.commit()
    return goal_state(session, customer_id)


def clear_goal(session: Session, customer_id: str) -> GoalOut:
    goal = session.get(WeightGoal, customer_id)
    if goal is not None:
        session.delete(goal)
        session.commit()
    return goal_state(session, customer_id)

"""饮食记录：一句话描述 → 服务端估算热量与三大营养素 → 落库与当日汇总。"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import local_day_end_utc, local_day_start_utc, local_today, to_utc_naive
from app.core.errors import conflict, invalid, not_found
from app.logic import nutrition
from app.models.herlog import Meal
from app.schemas.weight_plus import (
    DailyNutritionOut,
    MacroOut,
    MealEstimateOut,
    MealIn,
    MealOut,
    meal_out,
)
from app.services import goal_service, weight_ai


def _same_content(row: Meal, payload: MealIn, eaten_at_utc) -> bool:
    return (
        row.text == payload.text
        and row.meal_type == payload.meal_type
        and row.eaten_at == eaten_at_utc
    )


def analyze(text: str, meal_type: str = "加餐") -> MealEstimateOut:
    if meal_type not in nutrition.MEAL_TYPES:
        raise invalid(f"餐次只能是：{'、'.join(nutrition.MEAL_TYPES)}")
    return weight_ai.estimate_meal(text, meal_type)


def create_meal(session: Session, customer_id: str, payload: MealIn) -> tuple[MealOut, bool]:
    """同账号同 client_key 幂等：内容一致返回原记录，内容不同 409。"""

    eaten_at_utc = to_utc_naive(payload.eaten_at)
    existing = session.scalar(
        select(Meal).where(Meal.customer_id == customer_id, Meal.client_key == payload.client_key)
    )
    if existing is not None:
        if _same_content(existing, payload, eaten_at_utc):
            return meal_out(existing), False
        raise conflict("该请求已用于另一条饮食记录，请刷新后重试")

    estimate = weight_ai.estimate_meal(payload.text, payload.meal_type)
    row = Meal(
        customer_id=customer_id,
        client_key=payload.client_key,
        eaten_at=eaten_at_utc,
        meal_type=payload.meal_type,
        text=payload.text,
        kcal=estimate.kcal,
        protein_g=estimate.protein_g,
        carb_g=estimate.carb_g,
        fat_g=estimate.fat_g,
        estimate_source="fixture" if estimate.demo_sample else "model",
    )
    session.add(row)
    session.commit()
    return meal_out(row), True


def list_meals(session: Session, customer_id: str, day: date) -> list[MealOut]:
    rows = session.scalars(
        select(Meal)
        .where(
            Meal.customer_id == customer_id,
            Meal.eaten_at >= local_day_start_utc(day),
            Meal.eaten_at < local_day_end_utc(day),
        )
        .order_by(Meal.eaten_at.asc(), Meal.id.asc())
    ).all()
    return [meal_out(row) for row in rows]


def delete_meal(session: Session, customer_id: str, meal_id: int) -> None:
    row = session.scalar(select(Meal).where(Meal.id == meal_id, Meal.customer_id == customer_id))
    if row is None:
        raise not_found()
    session.delete(row)
    session.commit()


def _range_totals(session: Session, customer_id: str, day_from: date, day_to: date) -> tuple[int, int, int, int, int]:
    row = session.execute(
        select(
            func.count(Meal.id),
            func.coalesce(func.sum(Meal.kcal), 0),
            func.coalesce(func.sum(Meal.protein_g), 0),
            func.coalesce(func.sum(Meal.carb_g), 0),
            func.coalesce(func.sum(Meal.fat_g), 0),
        ).where(
            Meal.customer_id == customer_id,
            Meal.eaten_at >= local_day_start_utc(day_from),
            Meal.eaten_at < local_day_end_utc(day_to),
        )
    ).one()
    return int(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4])


def daily(session: Session, customer_id: str, day: date | None = None) -> DailyNutritionOut:
    target_day = day or local_today()
    if target_day > local_today():
        raise invalid("不能查看未来日期的饮食")
    meals = list_meals(session, customer_id, target_day)
    intake = sum(item.kcal for item in meals)
    protein = sum(item.protein_g for item in meals)
    carb = sum(item.carb_g for item in meals)
    fat = sum(item.fat_g for item in meals)
    target = goal_service.intake_target(session, customer_id)
    remaining, message = nutrition.energy_gap(intake, target)
    macros = nutrition.macro_percent(protein, carb, fat)
    return DailyNutritionOut(
        day=target_day.isoformat(),
        target_kcal=target,
        intake_kcal=intake,
        remaining_kcal=remaining,
        macros=MacroOut(carb=macros["carb"], protein=macros["protein"], fat=macros["fat"]),
        meals=meals,
        message=message,
    )


def week_average_kcal(session: Session, customer_id: str, days: int = 7) -> tuple[int, int]:
    """近 N 天：（有记录的天数，日均摄入 kcal）；没有记录时返回 (0, 0)。"""

    today = local_today()
    start = today - timedelta(days=days - 1)
    recorded, total_kcal, _, _, _ = _range_totals(session, customer_id, start, today)
    return recorded, (0 if recorded == 0 else round(total_kcal / recorded))

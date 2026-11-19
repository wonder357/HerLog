"""体重管理口径：BMI、能量消耗、目标进度与趋势预测。

数字口径来自《体重管理指导原则（2024 年版）》：中国成人 BMI 切点 18.5 / 24.0 / 28.0，
减重速度建议每周 0.5~1 kg（BMI 正常者按更温和的一半处理），每日能量缺口 500 kcal 且不低于基础代谢。
这里只做纯计算，不读写数据库，前端 `client/src/shared/weight.ts` 用同一套规则。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

BMI_LOW = 18.5
BMI_OVERWEIGHT = 24.0
BMI_OBESE = 28.0

NORMAL_RATE_RANGE = (250, 500)
HIGH_RATE_RANGE = (500, 1000)
DAILY_DEFICIT_KCAL = 500
ACTIVITY_FACTOR = 1.375
MIN_FORECAST_POINTS = 3
MAX_FORECAST_DAYS = 365


@dataclass(frozen=True)
class GoalProgress:
    percent: float
    remaining_grams: int
    reached: bool
    message: str


def bmi_value(grams: int, height_cm: Decimal | float | None) -> float | None:
    if height_cm is None:
        return None
    meters = float(height_cm) / 100
    if meters <= 0:
        return None
    return round(grams / 1000 / (meters**2), 1)


def bmi_category(value: float | None) -> str:
    if value is None:
        return "未知"
    if value < BMI_LOW:
        return "偏低"
    if value < BMI_OVERWEIGHT:
        return "正常"
    if value < BMI_OBESE:
        return "超重"
    return "肥胖"


def bmi_advice(value: float | None) -> str:
    category = bmi_category(value)
    if category == "未知":
        return "补充身高后可以算出 BMI。"
    if category == "偏低":
        return "BMI 低于 18.5，先保证吃够和睡够，不建议再减重。"
    if category == "正常":
        return "BMI 在 18.5~23.9 的正常区间，维持比继续减更重要。"
    if category == "超重":
        return "BMI 在 24~27.9，减重以每周 0.5~1 kg 的速度更稳。"
    return "BMI 达到 28 及以上，建议先做一次体检，再在医生指导下减重。"


def age_of(birthday: date | None, today: date) -> int | None:
    if birthday is None or birthday > today:
        return None
    years = today.year - birthday.year
    if (today.month, today.day) < (birthday.month, birthday.day):
        years -= 1
    return years if 0 < years < 120 else None


def bmr_kcal(grams: int, height_cm: Decimal | float | None, age: int | None) -> int | None:
    """Mifflin-St Jeor 女性公式；缺身高或年龄时返回 None，不硬编一个数出来。"""

    if height_cm is None or age is None:
        return None
    raw = 10 * (grams / 1000) + 6.25 * float(height_cm) - 5 * age - 161
    return int(round(raw))


def tdee_kcal(bmr: int | None) -> int | None:
    if bmr is None:
        return None
    return int(round(bmr * ACTIVITY_FACTOR))


def intake_target_kcal(tdee: int | None, bmr: int | None) -> int | None:
    """每日摄入目标：总消耗减 500 kcal，但绝不低于基础代谢。"""

    if tdee is None or bmr is None:
        return None
    return max(tdee - DAILY_DEFICIT_KCAL, bmr)


def rate_bounds_grams(bmi: float | None) -> tuple[int, int]:
    if bmi is not None and bmi >= BMI_OVERWEIGHT:
        return HIGH_RATE_RANGE
    return NORMAL_RATE_RANGE


def clamp_rate_grams(rate_grams: int, bmi: float | None) -> int:
    low, high = rate_bounds_grams(bmi)
    return max(low, min(high, rate_grams))


def goal_progress(start_grams: int, target_grams: int, current_grams: int | None) -> GoalProgress:
    """进度按「已走的距离 / 起点到目标的距离」，超出两端时钳在 0~100%。"""

    total = start_grams - target_grams
    if current_grams is None:
        return GoalProgress(0.0, max(total, 0), False, "还没有体重记录，先记一笔才能算进度。")
    remaining = current_grams - target_grams
    if total == 0:
        return GoalProgress(100.0 if remaining <= 0 else 0.0, max(remaining, 0), remaining <= 0,
                            "起点已经是目标体重，保持记录即可。")
    percent = round((start_grams - current_grams) / total * 100, 1)
    percent = max(0.0, min(100.0, percent))
    if remaining <= 0:
        return GoalProgress(100.0, 0, True, "已经到达目标体重，接下来以维持为主。")
    return GoalProgress(percent, remaining, False, f"距离目标还差 {remaining / 1000:.1f} kg。")


def slope_grams_per_day(points: list[tuple[date, int]]) -> float | None:
    """最小二乘斜率；少于 3 个数据点或天数不足时不预测，避免把波动当趋势。"""

    if len(points) < MIN_FORECAST_POINTS:
        return None
    ordered = sorted(points)
    base = ordered[0][0]
    xs = [(day - base).days for day, _ in ordered]
    ys = [grams for _, grams in ordered]
    if max(xs) - min(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    return numerator / denominator


def forecast_day(points: list[tuple[date, int]], target_grams: int) -> date | None:
    """按当前斜率外推到达目标体重的日期；方向不对、已达标或超过一年都返回 None。"""

    slope = slope_grams_per_day(points)
    if slope is None:
        return None
    current_day, current_grams = sorted(points)[-1]
    remaining = target_grams - current_grams
    if remaining == 0:
        return current_day
    if (remaining < 0 and slope >= 0) or (remaining > 0 and slope <= 0):
        return None
    days = remaining / slope
    if days < 0 or days > MAX_FORECAST_DAYS:
        return None
    return current_day + timedelta(days=int(round(days)))


def moving_average(grams_list: list[int], window: int = 7) -> float | None:
    if not grams_list:
        return None
    usable = grams_list[-window:]
    return round(sum(usable) / len(usable), 1)


def streak_days(days: list[date], today: date) -> int:
    """连续记录天数：今天没记也从昨天往前数，避免白天显示中断。"""

    if not days:
        return 0
    recorded = set(days)
    cursor = today if today in recorded else today - timedelta(days=1)
    streak = 0
    while cursor in recorded:
        streak += 1
        cursor -= timedelta(days=1)
    return streak

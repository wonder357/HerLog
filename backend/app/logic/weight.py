"""体重统计：与前端 `client/src/shared/weight.ts` 同一口径（每天取最后一次、按自然日）。

输入是「测量时间」的 UTC naive 值，输出按 Asia/Shanghai 自然日聚合。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.core.clock import to_local

MAX_KG = Decimal("999.999")
MAX_NOTES = 500


@dataclass(frozen=True)
class WeightRow:
    id: int
    grams: int
    measured_at: datetime
    tag: str | None = None
    note: str | None = None
    body_fat_pct: float | None = None


@dataclass(frozen=True)
class WeightPoint:
    day: date
    grams: int
    weight_id: int
    measured_at: datetime
    body_fat_pct: float | None = None


@dataclass(frozen=True)
class WeightSummary:
    days: int
    latest_grams: int | None
    latest_measured_at: datetime | None
    count: int
    points: list[WeightPoint] = field(default_factory=list)
    delta_grams: int | None = None

    @property
    def delta_kg(self) -> float | None:
        if self.delta_grams is None:
            return None
        return round(self.delta_grams / 1000, 3)


def parse_kg(raw: str | int | float | Decimal) -> int:
    """kg → 正整数克；最多三位小数。"""

    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("体重格式不正确") from exc
    if not value.is_finite():
        raise ValueError("体重格式不正确")
    if value != value.quantize(Decimal("0.001")):
        raise ValueError("体重最多三位小数")
    grams = int((value * 1000).to_integral_value(rounding=ROUND_HALF_UP))
    if grams <= 0:
        raise ValueError("体重需为正数")
    if value > MAX_KG:
        raise ValueError("体重超出可用范围")
    return grams


def format_kg(grams: int | None) -> str | None:
    if grams is None:
        return None
    text = f"{grams / 1000:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def daily_points(rows: list[WeightRow]) -> list[WeightPoint]:
    """同一自然日只保留最后一次测量；按日期升序返回。

    体脂率取同一次测量的值，不与另一笔的体重拼接，避免出现「晚上的体重 + 早上的体脂」。
    """

    latest: dict[date, WeightPoint] = {}
    for row in rows:
        day = to_local(row.measured_at).date()
        candidate = WeightPoint(day, row.grams, row.id, row.measured_at, row.body_fat_pct)
        current = latest.get(day)
        if current is None or (candidate.measured_at, candidate.weight_id) > (
            current.measured_at,
            current.weight_id,
        ):
            latest[day] = candidate
    return [latest[day] for day in sorted(latest)]


def summarize(rows: list[WeightRow], days: int, today: date) -> WeightSummary:
    """days=7/30：范围内记录次数统计全部测量，图表取每日最后一次，首尾按图上两点求差。"""

    if days not in (7, 30):
        raise ValueError("days 只支持 7 或 30")
    start_day = today - timedelta(days=days - 1)
    in_range = [row for row in rows if start_day <= to_local(row.measured_at).date() <= today]
    points = daily_points(in_range)
    delta = points[-1].grams - points[0].grams if len(points) >= 2 else None
    latest_row = max(rows, key=lambda row: (row.measured_at, row.id)) if rows else None
    return WeightSummary(
        days=days,
        latest_grams=latest_row.grams if latest_row else None,
        latest_measured_at=latest_row.measured_at if latest_row else None,
        count=len(in_range),
        points=points,
        delta_grams=delta,
    )


def suggestion(summary: WeightSummary) -> str | None:
    """一条与当前记录情况相关的建议；没有合适建议时返回 None（前端收起该区域）。"""

    if summary.count == 0:
        return None
    if len(summary.points) <= 1:
        return "先继续记录几天，再来看看变化趋势。"
    if summary.count > len(summary.points):
        return "如果想比较长期变化，尽量在相近的时间和条件下称重。"
    if summary.delta_grams is not None and abs(summary.delta_grams) < 200:
        return "这段时间体重变化很小，继续按自己的节奏记录即可。"
    return "想看得更准，可以固定早晨空腹、同一台秤称重。"


def range_start(days: int, today: date) -> date:
    return today - timedelta(days=days - 1)


@dataclass(frozen=True)
class MetricChange:
    """一段时间的首值、末值与变化量；不足两个点时不给变化量。"""

    first: float | None = None
    last: float | None = None
    delta: float | None = None


def metric_change(values: list[float]) -> MetricChange:
    if not values:
        return MetricChange()
    first, last = round(values[0], 3), round(values[-1], 3)
    return MetricChange(
        first=first,
        last=last,
        delta=None if len(values) < 2 else round(last - first, 3),
    )


def body_fat_points(points: list[WeightPoint]) -> list[tuple[date, float]]:
    """只保留真正记录过体脂率的那几天，不插值、不拿相邻日补齐。"""

    return [
        (point.day, round(point.body_fat_pct, 1))
        for point in points
        if point.body_fat_pct is not None
    ]


def fat_mass_kg(grams: int, body_fat_pct: float | None) -> float | None:
    """体脂量 = 体重 × 体脂率；体脂率缺失时返回 None，不猜。"""

    if body_fat_pct is None:
        return None
    return round(grams / 1000 * body_fat_pct / 100, 2)


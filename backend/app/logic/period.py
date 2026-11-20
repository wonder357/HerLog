"""经期预测：与前端 `client/src/shared/period.ts` 一一对应，两侧都不得依赖大模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import islice
from typing import Iterable, Sequence

MAX_STARTS = 4
MIN_STARTS = 3
MAX_SPREAD_DAYS = 7

INSUFFICIENT = "insufficient"
IRREGULAR = "irregular"
UPCOMING = "upcoming"
OVERDUE = "overdue"


@dataclass(frozen=True)
class Prediction:
    status: str
    expected_start: date | None = None
    estimate_days: int | None = None
    cycle_count: int = 0
    starts_used: int = 0

    @property
    def message(self) -> str:
        if self.status == INSUFFICIENT:
            return "再记录几次经期开始日期，就能估算下次日期"
        if self.status == IRREGULAR:
            return "近期周期变化较大，暂不显示预计日期"
        if self.status == OVERDUE:
            return "已过预计日期，尚未记录新的经期开始"
        assert self.expected_start is not None
        return f"预计下次开始：{self.expected_start.month} 月 {self.expected_start.day} 日"


def recent_starts(starts: Iterable[date], limit: int = MAX_STARTS) -> list[date]:
    """去重后按开始日倒序，最多返回 limit 条。"""

    return sorted(set(starts), reverse=True)[:limit]


def cycle_intervals(starts: Sequence[date]) -> list[int]:
    ordered = list(starts)
    return [(ordered[i] - ordered[i + 1]).days for i in range(len(ordered) - 1)]


def estimate_cycle_days(starts: Sequence[date]) -> tuple[int | None, list[int]]:
    """返回 (估算周期天数, 参与计算的周期列表)。不足三条或波动过大时天数为 None。"""

    ordered = recent_starts(starts)
    if len(ordered) < MIN_STARTS:
        return None, []
    intervals = cycle_intervals(ordered)
    if max(intervals) - min(intervals) > MAX_SPREAD_DAYS:
        return None, intervals
    if len(intervals) == 3:
        return sorted(intervals)[1], intervals
    average = Decimal(sum(intervals)) / Decimal(len(intervals))
    return int(average.quantize(Decimal(1), rounding=ROUND_HALF_UP)), intervals


def predict_next_start(starts: Sequence[date], today: date) -> Prediction:
    ordered = recent_starts(starts)
    if len(ordered) < MIN_STARTS:
        return Prediction(INSUFFICIENT, starts_used=len(ordered))
    estimate, intervals = estimate_cycle_days(ordered)
    if estimate is None:
        return Prediction(IRREGULAR, cycle_count=len(intervals), starts_used=len(ordered))
    expected = ordered[0] + timedelta(days=estimate)
    status = OVERDUE if today > expected else UPCOMING
    return Prediction(
        status=status,
        expected_start=expected if status == UPCOMING else None,
        estimate_days=estimate,
        cycle_count=len(intervals),
        starts_used=len(ordered),
    )


def ovulatory_window(next_start: date) -> tuple[date, date]:
    """日期估算使用的阶段区间，供周期上下文与月历共用。"""
    return next_start - timedelta(days=16), next_start - timedelta(days=12)


def duration_days(start_day: date, end_day: date | None) -> int | None:
    """持续天数包含开始日和最后一天。"""

    if end_day is None:
        return None
    return (end_day - start_day).days + 1


def estimate_period_end(expected_start: date, durations: Iterable[int | None]) -> date:
    """Use completed records for the calendar band; a lone duration is not enough."""

    sample = sorted(islice((days for days in durations if days is not None and 1 <= days <= 14), MAX_STARTS))
    if len(sample) < 2:
        return expected_start
    middle = len(sample) // 2
    days = (sample[(len(sample) - 1) // 2] + sample[middle] + 1) // 2
    return expected_start + timedelta(days=days - 1)


def build_history(rows: Sequence[tuple[int, date, date | None]]) -> list[dict]:
    """按开始日倒序生成历史周期：持续天数与距上次开始的间隔。"""

    ordered = sorted(rows, key=lambda row: row[1], reverse=True)
    history: list[dict] = []
    for index, (row_id, start_day, end_day) in enumerate(ordered):
        previous = ordered[index + 1][1] if index + 1 < len(ordered) else None
        history.append(
            {
                "id": row_id,
                "start_day": start_day,
                "end_day": end_day,
                "duration_days": duration_days(start_day, end_day),
                "cycle_days": (start_day - previous).days if previous else None,
            }
        )
    return history

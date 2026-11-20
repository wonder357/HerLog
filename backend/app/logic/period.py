"""经期预测：与前端 `client/src/shared/period.ts` 一一对应，两侧都不得依赖大模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Sequence

MAX_STARTS = 4
MIN_STARTS = 3
MAX_SPREAD_DAYS = 7

# 日历高亮所需的派生区间：预测经期长度、排卵日与易孕期，规则与前端
# `client/src/shared/period.ts` 的 estimateDurationDays / predictedRange /
# ovulationDay / fertileWindow 保持一致。
DEFAULT_DURATION_DAYS = 5
MIN_DURATION_DAYS = 2
MAX_DURATION_DAYS = 10
LUTEAL_DAYS = 14
FERTILE_BEFORE_OVULATION = 5
FERTILE_AFTER_OVULATION = 1

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
        expected_start=expected,
        estimate_days=estimate,
        cycle_count=len(intervals),
        starts_used=len(ordered),
    )


def ovulation_day(next_start: date) -> date:
    """排卵日：按黄体期 14 天从下次经期开始日回推。"""

    return next_start - timedelta(days=LUTEAL_DAYS)


def fertile_window(next_start: date) -> tuple[date, date]:
    """易孕期：排卵日前 5 天到排卵日后 1 天。"""

    day = ovulation_day(next_start)
    return (
        day - timedelta(days=FERTILE_BEFORE_OVULATION),
        day + timedelta(days=FERTILE_AFTER_OVULATION),
    )


def clamp_duration(duration_days: int) -> int:
    return max(MIN_DURATION_DAYS, min(MAX_DURATION_DAYS, duration_days))


def estimate_duration_days(durations: Iterable[int], limit: int = MAX_STARTS) -> int:
    """最近至多 4 段完整经期的平均持续天数，四舍五入后夹在 2–10 天。"""

    values = [value for value in list(durations)[:limit] if value]
    if not values:
        return DEFAULT_DURATION_DAYS
    average = Decimal(sum(values)) / Decimal(len(values))
    return clamp_duration(int(average.quantize(Decimal(1), rounding=ROUND_HALF_UP)))


def predicted_range(expected_start: date, duration_days: int) -> tuple[date, date]:
    """预计经期区间：开始日到开始日 + 持续天数 - 1。"""

    return expected_start, expected_start + timedelta(days=clamp_duration(duration_days) - 1)


def schedule_range(
    expected_start: date, today: date, duration_days: int = DEFAULT_DURATION_DAYS
) -> tuple[date, date, int]:
    """日历上真正高亮的预测经期区间。

    已经过了预计开始日却还没有新的经期记录时，预测不能让高亮停在过去：
    区间从今天起算，顺延天数逐日增加，直到用户补记新的开始日。
    返回 (区间开始, 区间结束, 顺延天数)。
    """

    overdue = max(0, (today - expected_start).days)
    start = expected_start + timedelta(days=overdue)
    end = start + timedelta(days=clamp_duration(duration_days) - 1)
    return start, end, overdue


def recent_durations(rows: Sequence[tuple[date, date | None]]) -> list[int]:
    """按开始日倒序取最近几段完整经期的持续天数。"""

    ordered = sorted(rows, key=lambda row: row[0], reverse=True)
    durations: list[int] = []
    for start_day, end_day in ordered:
        if end_day is not None:
            durations.append((end_day - start_day).days + 1)
    return durations


def duration_days(start_day: date, end_day: date | None) -> int | None:
    """持续天数包含开始日和最后一天。"""

    if end_day is None:
        return None
    return (end_day - start_day).days + 1


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

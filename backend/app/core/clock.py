"""统一时间口径：数据库存 UTC 的 naive DATETIME(3)，统计按 Asia/Shanghai 自然日。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from app.core.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_local(moment: datetime) -> datetime:
    """把库里的 UTC naive 时间转换为本地时间。"""

    return moment.replace(tzinfo=timezone.utc).astimezone(settings.tz)


def to_utc_naive(moment: datetime) -> datetime:
    """把带时区的时间转换为库中存储的 UTC naive 时间；naive 输入按本地时间解释。"""

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=settings.tz)
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def local_today() -> date:
    return datetime.now(settings.tz).date()


def local_day_start_utc(day: date) -> datetime:
    return to_utc_naive(datetime.combine(day, time.min))


def local_day_end_utc(day: date) -> datetime:
    return local_day_start_utc(day + timedelta(days=1))

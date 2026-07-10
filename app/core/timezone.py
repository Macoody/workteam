"""
业务时间工具。

系统对用户展示和业务记录统一使用北京时间。数据库中旧数据可能来自不同
时区，本模块负责把读写边界都收敛到 Asia/Shanghai 的本地时间。
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

BUSINESS_TZ = ZoneInfo(settings.BUSINESS_TIMEZONE)


def business_now() -> datetime:
    """当前北京时间，返回无时区 datetime，便于 MySQL DATETIME 和前端一致展示。"""
    return datetime.now(BUSINESS_TZ).replace(tzinfo=None)


def business_today() -> date:
    return datetime.now(BUSINESS_TZ).date()


def business_utc_offset() -> str:
    offset = datetime.now(BUSINESS_TZ).utcoffset()
    if offset is None:
        return "+08:00"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def parse_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    return datetime.fromisoformat(text)


def to_business_time(value) -> datetime | None:
    """把任意 datetime 归一成北京时间的无时区值。"""
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=None)
    return parsed.astimezone(BUSINESS_TZ).replace(tzinfo=None)


def day_bounds(value) -> tuple[datetime, datetime]:
    target = to_business_time(value) or business_now()
    start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end

import time
import datetime as dt
from typing import NewType

datetime_type = dt.datetime
datetime = NewType("datetime", dt.datetime)
timezone = NewType("timezone", dt.timezone)


def date_now(utc_offset: float) -> datetime:
    tz = dt.timezone(dt.timedelta(hours=utc_offset))
    return datetime(dt.datetime.now(tz))


def fromtimestamp(timestamp: float, utc_offset: float) -> datetime:
    tz = utc_offset_to_tz(utc_offset)
    return datetime(dt.datetime.fromtimestamp(timestamp, tz))


def utc_offset_to_tz(utc_offset: float) -> timezone:
    return timezone(dt.timezone(dt.timedelta(hours=utc_offset)))


def local_tz() -> timezone:
    offset = float(time.timezone) if (time.localtime().tm_isdst == 0) else time.altzone
    offset = offset / 60 / 60 * -1
    return utc_offset_to_tz(offset)

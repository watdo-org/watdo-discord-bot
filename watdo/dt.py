import datetime as dt
from typing import NewType

datetime_type = dt.datetime
datetime = NewType("datetime", dt.datetime)


def date_now(utc_offset_hour: float) -> datetime:
    tz = dt.timezone(dt.timedelta(hours=utc_offset_hour))
    return datetime(dt.datetime.now(tz))


def fromtimestamp(timestamp: float, utc_offset_hour: float) -> datetime:
    tz = utc_offset_hour_to_tz(utc_offset_hour)
    return datetime(dt.datetime.fromtimestamp(timestamp, tz))


def utc_offset_hour_to_tz(utc_offset_hour: float) -> dt.timezone:
    return dt.timezone(dt.timedelta(hours=utc_offset_hour))

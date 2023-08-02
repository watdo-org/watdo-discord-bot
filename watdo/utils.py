import datetime as dt


def datetime_now(utc_offset_hour: float) -> dt.datetime:
    tz = dt.timezone(dt.timedelta(hours=utc_offset_hour))
    return dt.datetime.now(tz)

import datetime

import pytz


def _to_timezone(value, timezone):
    """
    Converts an aware datetime.datetime to the given time.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # This method is available for pytz time zones.
        value = timezone.normalize(value)
    return value


def convert_sp_and_date_to_utc(sp, date, timezone="Europe/London"):
    """
    Return the datetime for the start of a given settlement period.

    We assume the time of the first SP period of the day is 00:00 local time.

    :param sp: Integer representing the settlement period (between 1 and 48)
    :param date: date object
    :param string: The local timezone of the date
    :return: UTC representation of the given SP and Date
    """
    local_midnight = pytz.timezone(timezone).localize(
        datetime.datetime(date.year, date.month, date.day, hour=0, minute=0, second=0))
    return _to_timezone(local_midnight, pytz.UTC) + datetime.timedelta(minutes=(sp - 1) * 30)


def convert_utc_to_sp_and_date(utc_datetime, timezone="Europe/London"):
    """
    Convert a timezone-naive datetime object, in UTC, to a SP (Settlement Period) and Date
    combination.

    :param utc_datetime: datetime timezone-aware object in UTC
    """
    # Flatten the minutes to the nearest half hour
    if utc_datetime.minute < 30:
        minutes = 0
    else:
        minutes = 30
    utc_datetime = utc_datetime.replace(minute=minutes)

    # Convert dt to localtime
    local_timezone = pytz.timezone(timezone)
    local_dt = _to_timezone(utc_datetime, local_timezone)

    # We re-create the midnight object so the DST settings are correct
    d = datetime.datetime(local_dt.year, local_dt.month, local_dt.day)
    local_midnight = local_timezone.localize(d, local_timezone)

    delta = local_dt - local_midnight
    minutes_delta = (delta.seconds // 60) + 30
    sp = minutes_delta // 30
    return sp, local_dt.date()

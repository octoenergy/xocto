import datetime

import pytz


def to_timezone(value, timezone):
    """
    Converts an aware datetime.datetime to the given time.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # This method is available for pytz time zones.
        value = timezone.normalize(value)
    return value


def is_dst(timezone):
    now = pytz.utc.localize(datetime.datetime.utcnow())
    return now.astimezone(timezone).dst() != datetime.timedelta(0)


def convert_sp_and_date_to_utc(sp, date):
    """
    Convert a SP (Settlement Period) and Date combination into a UTC date.
    We assume the time of the first SP period of the day is 00:00 local time.
    :param sp: Integer representing the settlement period
    :param date: date/datetime object
    :return: UTC representation of the given SP and Date
    """
    # We reduce 1 from the SP so we can multiply
    # it properly by 30, the half-hour period.
    # The First SP of the day is 00:00.
    sp -= 1
    minutes = sp * 30

    london_timezone = pytz.timezone('Europe/London')
    london_midnight = london_timezone.localize(
        datetime.datetime(date.year, date.month, date.day, hour=0, minute=0, second=0))

    utc_start_of_day = to_timezone(london_midnight, pytz.UTC)
    utc_time = utc_start_of_day + datetime.timedelta(minutes=minutes)
    return utc_time


def convert_utc_to_sp_and_date(utc_datetime):
    """
    Convert a timezone-naive datetime object, in UTC,
    to a SP (Settlement Period) and Date combination.
    :param utc_datetime: datetime timezone-aware object in UTC
    """
    """
    Convert a datetime object, in UTC,
    to a SP (Settlement Period) and Date combination.
    """

    if utc_datetime.minute < 30:
        minutes = 0
    else:
        minutes = 30

    utc_datetime = utc_datetime.replace(minute=minutes)

    london_timezone = pytz.timezone('Europe/London')
    london_datetime = to_timezone(utc_datetime, london_timezone)
    # We re-create the midnight object so the DST settings are correct
    d = datetime.datetime(london_datetime.year, london_datetime.month, london_datetime.day)
    london_midnight = london_timezone.localize(d, london_timezone)

    delta = london_datetime - london_midnight
    minutes_delta = (delta.seconds // 60) + 30
    sp = minutes_delta // 30

    date = utc_datetime.astimezone(london_timezone)
    return sp, date.date()

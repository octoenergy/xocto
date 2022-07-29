import calendar
import datetime as datetime_
import decimal
from typing import Generator, Optional, Sequence, Tuple, Union

import pytz
from dateutil import tz
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from . import numbers, ranges

# Convenience type aliases for referencing from other modules. The 'Union` is redundant and just
# to help mypy realise that these are type aliases, not assignments.
Date = Union[datetime_.date]
DateTime = Union[datetime_.datetime]
DateOrDatetime = Union[Date, DateTime]
Time = Union[datetime_.time]
TimeDelta = Union[datetime_.timedelta]

# Timezone aware datetime in the far future.
far_future = timezone.make_aware(datetime_.datetime.max - datetime_.timedelta(days=2))

# Timezone aware datetime in the far past.
far_past = timezone.make_aware(datetime_.datetime.min + datetime_.timedelta(days=2))

UTC = datetime_.timezone.utc
LONDON = pytz.timezone("Europe/London")

ONE_DAY = datetime_.timedelta(days=1)
ONE_HOUR = datetime_.timedelta(hours=1)

MIDNIGHT_TIME = datetime_.time(0, 0)


def as_localtime(dt, tz=None):
    """
    Convert a tz aware datetime to localtime.

    Wrapper for the django.utils.timezone function, taking the same arguments.
    """
    return timezone.localtime(dt, timezone=tz)


def as_utc(dt):
    """
    Wrapper for normalizing a datetime aware object into UTC.
    """
    return as_localtime(dt, datetime_.timezone.utc)


def now() -> datetime_.datetime:
    """
    Return the current datetime in the local timezone.
    """
    return as_localtime(timezone.now())


def datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0, is_dst=None):
    """
    Return a datetime in the local timezone.

    A boolean value is required for is_dst to unambiguously determine the appropriate dt during the
    window when the hour goes back.
    """
    dt = datetime_.datetime(year, month, day, hour, minute, second, microsecond)
    return timezone.make_aware(dt, is_dst=is_dst)


# Returning dates


def date(dt: datetime_.datetime, tz=None) -> datetime_.date:
    """
    Return the date of the given datetime in the given timezone, defaulting to local time.

    Note that `dt` must already be timezone-aware: it cannot be naive. It may be in UTC, for
    example, or already in current local time, in which case the effect will be the same as
    calling `.date()` on it. If `tz` is not provided, the function will return the date of `dt` in
    the local time zone.
    """
    if dt is None:
        # This is necessary as as_localtime is fine with being passed None, but we don't want to
        # accidentally do that here (since we have today as a separate method).
        raise TypeError("You must supply a datetime to localtime.date")

    return as_localtime(dt, tz=tz).date()


def today(tz=None) -> datetime_.date:
    """
    Return the current date in the provided timezone (or the local timezone if none is supplied).
    """
    return date(timezone.now(), tz=tz)


def yesterday(tz=None) -> datetime_.date:
    """
    Return the previous date in the provided timezone (or the local timezone if none is supplied).
    """
    return days_in_the_past(1, tz=tz)


def tomorrow(tz=None) -> datetime_.date:
    """
    Return the next date in the provided timezone (or the local timezone if none is supplied).
    """
    return days_in_the_future(1, tz=tz)


def days_in_the_past(n: int, tz=None) -> datetime_.date:
    """
    Return n days before the current date (in the provided or local timezone).
    """
    return today(tz=tz) - relativedelta(days=n)


def days_in_the_future(n: int, tz=None) -> datetime_.date:
    """
    Return n days after the current date (in the provided or local timezone).
    """
    return today(tz=tz) + relativedelta(days=n)


def months_in_the_past(n: int, tz=None) -> datetime_.date:
    """
    Return n months before the current date (in the provided or local timezone).
    """
    return today(tz=tz) - relativedelta(months=n)


def months_in_the_future(n: int, tz=None) -> datetime_.date:
    """
    Return n months after the current date (in the provided or local timezone).
    """
    return today(tz=tz) + relativedelta(months=n)


def date_of_day_before(dt: datetime_.datetime, tz=None) -> datetime_.date:
    """
    Return the date of the day before the datetime passed in.

    That is, find the local date of the datetime passed in, subtract one day from it, and return it.

    This is frequently useful when we are converting from the upper bound of a datetime range,
    which by convention we treat as exclusive, to the upper bound of a date range, which by
    convention we consider *inclusive*.

    Note that `dt` must already be timezone-aware: it cannot be naive. It may be in UTC, for
    example, or already in current local time, in which case the effect will be the same as
    calling `.date()` on it and subtracting a day. If `tz` is not provided, the function will
    return the date before `dt` in the local time zone.
    """
    return day_before(date(dt, tz=tz))


def day_before(d: datetime_.date) -> datetime_.date:
    return d - datetime_.timedelta(days=1)


def day_after(d: datetime_.date) -> datetime_.date:
    return d + datetime_.timedelta(days=1)


# Returning datetimes


def seconds_in_the_future(n: int, dt: Optional[datetime_.datetime] = None) -> datetime_.datetime:
    """
    Return a datetime of the number of specifed seconds in the future.
    """
    if dt is None:
        dt = now()

    return dt + relativedelta(seconds=n)


def seconds_in_the_past(n) -> datetime_.datetime:
    """
    Return a datetime of the number of specifed seconds in the past.
    """
    return now() - relativedelta(seconds=n)


# Converting dates into datetimes


def midnight(
    date_or_datetime: Optional[DateOrDatetime] = None, tz: Optional[datetime_.tzinfo] = None
) -> datetime_.datetime:
    """
    Return a TZ-aware datetime for midnight of the passed date.

    If date is None then the current date in the passed timezone is used (if no timezone is
    supplied then we use the local timezone).
    """
    if date_or_datetime is None:
        date_: Date = today(tz=tz)
    elif isinstance(date_or_datetime, datetime_.datetime):
        # Although this function is meant to be used on dates, we want to handle datetimes
        # properly as well, as these are frequently passed in as a way of 'truncating' them to
        # midnight on that date.
        if timezone.is_naive(date_or_datetime):
            # Default to localtime if no tz provided, as_localtime takes tz aware args
            date_ = date(timezone.make_aware(date_or_datetime), tz=tz)
        else:
            date_ = date(date_or_datetime, tz=tz)
    else:
        date_ = date_or_datetime

    naive_midnight = datetime_.datetime.combine(date_, datetime_.datetime.min.time())
    return timezone.make_aware(naive_midnight, timezone=tz)


def next_midnight(
    date_or_datetime: Optional[DateOrDatetime] = None, tz: Optional[datetime_.tzinfo] = None
) -> datetime_.datetime:
    """
    Return the datetime for midnight of the following day to the date passed in.

    This is intuitively what people think of as midnight.
    """
    if date_or_datetime is None:
        date_: Date = today(tz=tz)
    elif isinstance(date_or_datetime, datetime_.datetime):
        # Although this function is meant to be used on dates, we want to handle datetimes
        # properly as well
        if timezone.is_naive(date_or_datetime):
            # Default to localtime if no tz provided, as_localtime takes tz aware args
            date_ = date(timezone.make_aware(date_or_datetime), tz=tz)
        else:
            date_ = date(date_or_datetime, tz=tz)
    else:
        date_ = date_or_datetime

    return midnight(date_ + datetime_.timedelta(days=1), tz=tz)


def midday(_date=None, tz=None) -> datetime_.datetime:
    """
    Return a TZ-aware datetime for midday of the passed date.

    If date is None then the current date in the passed timezone is used (if no timezone is
    supplied then we use the local timezone).
    """
    if _date is None:
        _date = today(tz=tz)

    return datetime_from_date(_date, hour=12, tz=tz)


def datetime_from_date(_date, hour, tz=None):
    """
    Return a TZ-aware datetime for the hour of the passed date.
    """
    naive_datetime = datetime_.datetime.combine(_date, datetime_.time(hour))
    return timezone.make_aware(naive_datetime, timezone=tz)


def datetime_from_epoch_timestamp(timestamp, tz=None):
    naive_datetime_in_utc = datetime_.datetime.utcfromtimestamp(timestamp)
    utc_dt = timezone.make_aware(naive_datetime_in_utc, timezone=UTC)
    dt = timezone.localtime(utc_dt, timezone=tz)
    return dt


def latest(_date=None, tz=None):
    """
    Return a TZ-aware datetime for the latest representable datetime of the passed date.

    If date is None then the current date in the local timezone is used.
    """
    if _date is None:
        _date = today()
    naive_midnight = datetime_.datetime.combine(_date, datetime_.datetime.max.time())
    return timezone.make_aware(naive_midnight, timezone=tz)


def combine(_date: datetime_.date, _time: datetime_.time, tz) -> datetime_.datetime:
    combined_dt = datetime_.datetime.combine(_date, _time)
    if tz is datetime_.timezone.utc:
        return combined_dt.replace(tzinfo=tz)
    return tz.localize(combined_dt)


# Converting dates into datetime pairs


def date_boundaries(
    _date: Optional[Date], tz: Optional[datetime_.tzinfo] = None
) -> Tuple[DateTime, DateTime]:
    """
    Return a 2-tuple with the start and ending dt for the given date in the local timezone.

    Note, be careful of using this with __range ORM queries as such queries are INCLUSIVE on the
    boundaries.
    """
    return midnight(_date, tz=tz), next_midnight(_date, tz=tz)


def month_boundaries(month: int, year: int) -> Tuple[datetime_.datetime, datetime_.datetime]:
    """
    Return the boundary datetimes of a given month.
    """
    start_date = datetime_.date(year, month, 1)
    end_date = start_date + relativedelta(months=1)
    return (midnight(start_date), midnight(end_date))


def as_range(
    _date: Optional[Date], tz: Optional[datetime_.tzinfo] = None
) -> Tuple[DateTime, DateTime]:
    """
    Return a 2-tuple of the min and max datetimes for the given date.

    This gives values that can be passed to the ORM __range filter.
    """
    return midnight(_date, tz=tz), latest(_date, tz=tz)


def make_aware_assuming_local(dt):
    """
    Just a wrapper for Django's method, which will takes a naive datetime, and makes it timezone
    aware, assuming the current timezone if none is passed (which it isn't from this wrapper
    function). It will also raise an exception if the passed datetime is already timezone-aware.
    """
    return timezone.make_aware(dt, is_dst=True)


def make_aware_assuming_utc(dt):
    """
    Return a timezone-aware datetime (in UTC) given a naive datetime.
    """
    return timezone.make_aware(dt, timezone=UTC)


def is_utc(dt: datetime_.datetime) -> bool:
    """
    Test whether a given (timezone-aware) datetime is in UTC time or not.
    """
    assert dt.tzinfo, "Must be an aware datetime"
    timezone_name = dt.tzinfo.tzname(None) or str(dt.tzinfo)
    return timezone_name.upper() == "UTC"


def is_local_time(dt):
    """
    Test whether a given (timezone-aware) datetime is in local time or not.
    """
    if dt.tzinfo is datetime_.timezone.utc:
        dt = dt.replace(tzinfo=pytz.utc)
    current_timezone = timezone.get_current_timezone()
    return current_timezone.normalize(dt).tzinfo == dt.tzinfo


def within_date_range(first_date, second_date, days=3):
    """
    Check if two dates are within a range from each other.
    """
    margin = datetime_.timedelta(days=days)
    return first_date - margin <= second_date <= first_date + margin


def quantise(
    dt: datetime_.datetime, timedelta: datetime_.timedelta, rounding=decimal.ROUND_HALF_EVEN
) -> datetime_.datetime:
    """
    'Round' a datetime to the nearest interval given by the `timedelta` argument.

    For example:

        >>>> quantise(datetime.datetime(2020, 4, 1, 23, 21), timedelta(minutes=15))
        datetime.datetime(2020, 4, 1, 23, 30)

    """
    # We simply convert the datetime we want to quantise into a timestamp and use
    # `numbers.quantise()` to quantise it, with the 'seconds' from the timedelta argument as our
    # base.
    timedelta_seconds = timedelta.days * 24 * 60 * 60 + timedelta.seconds
    dt_as_timestamp = dt.timestamp()
    quantised_dt_timestamp = numbers.quantise(
        dt_as_timestamp, timedelta_seconds, rounding=rounding
    )
    quantised_dt = datetime_.datetime.fromtimestamp(quantised_dt_timestamp, tz=dt.tzinfo)
    return as_localtime(quantised_dt)


def nearest_half_hour(dt):
    return quantise(dt, datetime_.timedelta(minutes=30))


def is_last_day_of_month(_date):
    next_day = _date + datetime_.timedelta(days=1)
    if _date.month != next_day.month:
        return True
    return False


def start_of_month(dt=None):
    """
    Return the start datetime of the month for dt passed - or of current month.
    """
    if not dt:
        dt = now()
    return midnight(dt + relativedelta(day=1))


def end_of_month(dt=None):
    """
    Return the start datetime of the month for dt passed - or of current month.
    """
    if not dt:
        dt = now()
    return midnight(dt + relativedelta(day=1, months=1))


def first_day_of_month(dt=None):
    """
    Return the start date of the month for dt passed - or of current month.
    """
    if dt is None:
        dt = now()
    return (dt + relativedelta(day=1)).date()


def last_day_of_month(dt=None):
    """
    Return the last date of the month for dt passed - or of current month.
    """
    if dt is None:
        dt = now()
    return (dt + relativedelta(day=31)).date()


def is_n_days_until_end_of_month(n_days: int) -> bool:
    """
    Return whether today + n days is the first of the next month.
    """
    n_days_from_now = today() + relativedelta(days=n_days)
    return n_days_from_now.day == 1


def is_date_within_date_range(date_in_question, start, end) -> bool:
    """
    Return whether a given date falls within the range of two other dates. This function assumes
    start < end.
    """
    return start <= date_in_question <= end


def is_in_the_past(dt) -> bool:
    """
    Test whether a datetime is in the past.

    Note that we treat the current time as 'in the past' for the sake of this test. This means
    that any given datetime will always return True for either this function or
    `is_in_the_future`.
    """
    if not timezone.is_aware(dt):
        raise ValueError("Datetime must be timezone-aware")
    return dt <= now()


def is_in_the_future(dt) -> bool:
    """
    Test whether a datetime is in the future.
    """
    if not timezone.is_aware(dt):
        raise ValueError("Datetime must be timezone-aware")
    return dt > now()


def is_future_date(_date) -> bool:
    """
    Test whether a date is in the future.
    """
    return _date > today()


def is_within_the_last_year(date: datetime_.date) -> bool:
    """
    Test whether a date is one year or less before today's local date.
    """
    return today() - relativedelta(years=1) <= date <= today()


def is_within_the_last_week(date: datetime_.date) -> bool:
    """
    Test whether a date is within a week ago of today's dates inclusive of the earliest date.
    """
    return today() - relativedelta(days=7) <= date <= today()


def latest_date_for_day(
    start_date: datetime_.date, end_date: datetime_.date, day_of_month: int
) -> Optional[datetime_.date]:
    """
    Given an integer day of a month, return the latest date with that day of the month,
    bounded by the supplied start_date and end_date. If no such date exists, return None.
    """
    if not (1 <= day_of_month <= 31):
        raise ValueError(f"{day_of_month} is not a valid day of the month.")

    date_range = ranges.FiniteRange(start_date, end_date, boundaries="[]")

    # Begin with a date in the same month as the end date.
    # (This will not necessarily be in range.)
    candidate_date = date_range.end + relativedelta(day=day_of_month)

    # Work our way backwards from the end date until we find a suitable date.
    while candidate_date >= date_range.start:
        if candidate_date.day == day_of_month and candidate_date in date_range:
            return candidate_date
        candidate_date -= relativedelta(months=1, day=day_of_month)
    return None


def next_date_with_day_of_month(date: datetime_.date, day_of_month: int) -> datetime_.date:
    """
    Given a starting `date`, return the next date with the specified `day_of_month`.

    If the day of the month doesn't exist in the next month, return the nearest date that does.

    For example:

        next_date_with_day_of_month(date=date(2020, 1, 31), day_of_month=31)

        :returns: date(2020, 2, 29).

    :raises TypeError: if a datetime is used for `date`
    :raises ValueError: if the day of month is invalid

    Note: Python's datetime is a subclass of date, so the type checker will not prevent passing it
    to this function.
    """

    if isinstance(date, datetime_.datetime):
        raise TypeError("Must use a date, not a datetime.")

    if not (1 <= day_of_month <= 31):
        raise ValueError(f"{day_of_month} is not a valid day of the month.")

    next_date = date.replace(day=day_of_month)

    if next_date <= date:
        next_date += relativedelta(months=1, day=day_of_month)

    return next_date


def date_iterator(
    start_date: datetime_.date, end_date: datetime_.date
) -> Generator[datetime_.date, None, None]:
    """
    Iterate through dates between two dates
    """
    date = start_date

    while date < end_date:
        yield date
        date = date + datetime_.timedelta(days=1)


def system_timezone():
    """
    Get the current system timezone.
    """
    return tz.tzlocal()


def is_dst(local_time: datetime_.datetime) -> bool:
    """
    Indicate whether the given time (and timezone is in daylight savings time (DST or not).

    Raises:
        pytz.exceptions.NonExistentTimeError if the time doesn't exist.
        pytz.exceptions.AmbiguousTimeError if the time exists in both DST and non-DST
        ValueError if `local_time` doesn't have any timezone information
    """
    if not local_time.tzinfo:
        raise ValueError("Can't determine DST for a naive datetime")

    localised_dt = local_time.tzinfo.normalize(local_time)  # type: ignore

    return bool(localised_dt.dst())


def is_localtime_midnight(dt: datetime_.datetime, tz: Optional[datetime_.tzinfo] = None) -> bool:
    """
    Return whether the supplied datetime is at midnight (in the site's local time zone).

    Note, the supplied datetime, which should be timezone aware, may be in any timezone,
    providing it corresponds to the moment of midnight in the site's local time zone.
    """
    return as_localtime(dt, tz=tz).time() == datetime_.time(0)


def is_aligned_to_midnight(range: ranges.FiniteDatetimeRange, tz=None) -> bool:
    """
    Return whether this range is aligned to localtime midnight.
    """
    return all(
        [is_localtime_midnight(range.start, tz=tz), is_localtime_midnight(range.end, tz=tz)]
    )


def consolidate_into_intervals(dates: Sequence[Date]) -> Sequence[Tuple[Date, Date]]:
    """
    Given a sequence of dates, return tuples of (inclusive) boundaries of the sub-sequences where
    the dates are consecutive.

    If a date does not form a continuous interval with any other dates - i.e. it is separated by at
    least a day before and after the others - it forms an interval with itself as both boundaries.

    For example, if passed:
    [
        <Date year=2020, month=1, day=1>,
        <Date year=2020, month=1, day=2>,
        <Date year=2020, month=1, day=4>,
        <Date year=2020, month=1, day=5>,
    ]
    it would return:
    [
        (<Date year=2020, month=1, day=1>, <Date year=2020, month=1, day=2>),
        (<Date year=2020, month=1, day=4>, <Date year=2020, month=1, day=5>),
    ]
    """
    if len(dates) < 1:
        raise ValueError("No dates provided.")

    dates = sorted(dates)
    intervals = []
    num_consecutive = 0

    interval_start, *remaining_dates = dates

    for i, date in enumerate(remaining_dates):
        if date == day_after(dates[i]):
            num_consecutive += 1
        else:
            intervals.append(
                (interval_start, interval_start + datetime_.timedelta(days=num_consecutive))
            )
            interval_start = date
            num_consecutive = 0

    intervals.append((interval_start, interval_start + datetime_.timedelta(days=num_consecutive)))

    return intervals


def translate_english_month_to_spanish(month: int) -> str:
    month_name = calendar.month_name[month]
    month_name_lookup = {
        "January": "enero",
        "February": "febrero",
        "March": "marzo",
        "April": "abril",
        "May": "mayo",
        "June": "junio",
        "July": "julio",
        "August": "agosto",
        "September": "septiembre",
        "October": "octubre",
        "November": "noviembre",
        "December": "deciembre",
    }
    return month_name_lookup[month_name]

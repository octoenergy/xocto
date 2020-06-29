import datetime
import typing

import pytz

from . import exceptions

__all__ = [
    "convert_sp_and_date_to_utc",
    "convert_utc_to_sp_and_date",
    "number_of_periods_in_timedelta",
]


# Time zones implemented
UTC_TZ = "UTC"
GB_TZ = "Europe/London"


def _to_timezone(local_time: datetime.datetime, timezone_str: str) -> datetime.datetime:
    """
    Converts an aware datetime to another time zone.
    """
    timezone = pytz.timezone(timezone_str)
    # Rebasing to local time zone
    rebased_local_time = local_time.astimezone(timezone)
    # Normalizing for daylight saving rules
    return timezone.normalize(rebased_local_time)


def _get_first_delivery_time(
    date: datetime.date, timezone_str: str, is_wholesale: bool
) -> datetime.datetime:
    """
    Return an aware datetime for the start of the first settlement period on a given date.
    """
    midnight = datetime.datetime(date.year, date.month, date.day)
    offset_midnight = midnight - datetime.timedelta(hours=1)
    # First settlement period
    cases = {
        # UTC: first delivery starts at 00:00:00 UTC on the day
        UTC_TZ: midnight,
        # GB retail: first delivery starts at 00:00:00 Europe/London on the day
        # GB wholesale: first delivery starts at 23:00:00 Europe/London on the previous day
        GB_TZ: offset_midnight if is_wholesale else midnight,
    }
    # Time zone aware
    try:
        return pytz.timezone(timezone_str).localize(cases[timezone_str])
    except AttributeError:
        raise exceptions.SettlementPeriodError("Time zone not implemented")


def _get_delivery_date(
    local_time: datetime.datetime, timezone_str: str, is_wholesale: bool
) -> datetime.date:
    """
    Return the date of the settlement period relative to a tz-aware datetime.
    """
    period_date = local_time.date()
    offset_period_date = period_date
    if local_time.hour >= 23:
        offset_period_date += datetime.timedelta(days=1)
    # Date of the first settlement period
    cases = {
        # UTC: first delivery starts at 00:00:00 UTC on the day
        UTC_TZ: period_date,
        # GB retail: first delivery starts at 00:00:00 Europe/London on the day
        # GB wholesale: first delivery starts at 23:00:00 Europe/London on the previous day
        GB_TZ: offset_period_date if is_wholesale else period_date,
    }
    # Time zone aware
    try:
        return cases[timezone_str]
    except AttributeError:
        raise exceptions.SettlementPeriodError("Time zone not implemented")


def _round_local_down_to_hh(local_time):
    if local_time.minute < 30:
        return local_time - datetime.timedelta(minutes=local_time.minute)
    else:
        return local_time - datetime.timedelta(minutes=local_time.minute - 30)


def convert_sp_and_date_to_local(
    sp: int, date: datetime.date, timezone_str: str, is_wholesale: bool
) -> datetime.datetime:
    """
    Return an aware datetime for the start of a given settlement period.
    """
    if sp not in range(1, 51):
        raise exceptions.SettlementPeriodError("Settlement period not valid")
    # First settlement period in the time zone
    first_period_start = _get_first_delivery_time(date, timezone_str, is_wholesale)
    # Start of the settlement period in local time
    local_time = first_period_start + datetime.timedelta(minutes=30 * (sp - 1))
    # Normalizing for daylight saving rules
    return pytz.timezone(timezone_str).normalize(local_time)


def convert_sp_and_date_to_utc(
    sp: int, date: datetime.date, timezone_str: str = GB_TZ, is_wholesale: bool = False
) -> datetime.datetime:
    """
    Return an UTC-aware datetime for the start of a given settlement period.
    """
    local_time = convert_sp_and_date_to_local(sp, date, timezone_str, is_wholesale)
    return _to_timezone(local_time, UTC_TZ)


def convert_local_to_sp_and_date(
    local_time: datetime.datetime, is_wholesale: bool = False
) -> typing.Tuple[int, datetime.date]:
    """
    Return the date and settlement period from a given tz-aware datetime.
    """
    try:
        timezone_str = str(local_time.tzinfo)
    except AttributeError:
        raise exceptions.SettlementPeriodError("Not a tz-aware datetime")
    # Round to the nearest half hour
    half_hourly_time = _round_local_down_to_hh(local_time)
    # Date of the settlement period in the time zone
    delivery_date = _get_delivery_date(half_hourly_time, timezone_str, is_wholesale)
    # First settlement period in the time zone
    first_delivery_time = _get_first_delivery_time(delivery_date, timezone_str, is_wholesale)
    # Fetch settlement period
    delta = half_hourly_time - first_delivery_time
    settlement_period = ((int(delta.total_seconds()) // 60) + 30) // 30
    return settlement_period, delivery_date


def convert_utc_to_sp_and_date(
    utc_time: datetime.datetime, timezone_str: str = GB_TZ, is_wholesale: bool = False
) -> typing.Tuple[int, datetime.date]:
    """
    Return the local date and settlement period from a given UTC-aware datetime.
    """
    local_time = _to_timezone(utc_time, timezone_str)
    return convert_local_to_sp_and_date(local_time, is_wholesale)


def number_of_periods_in_timedelta(delta: datetime.timedelta):
    """
    Return the number of half-hourly settlement periods in the given timedelta
    """
    return (delta.total_seconds() / 60) / 30

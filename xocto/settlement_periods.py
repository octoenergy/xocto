import datetime
import typing
import zoneinfo

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
    # With zoneinfo, astimezone resolves the target offset for the new
    # wall time, which is what pytz's localize/normalize dance worked around.
    return local_time.astimezone(zoneinfo.ZoneInfo(timezone_str))


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
        return cases[timezone_str].replace(tzinfo=zoneinfo.ZoneInfo(timezone_str))
    except (AttributeError, KeyError, zoneinfo.ZoneInfoNotFoundError):
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


def _round_local_down_to_hh(local_time: datetime.datetime) -> datetime.datetime:
    if local_time.minute < 30:
        rounded = local_time - datetime.timedelta(minutes=local_time.minute)
    else:
        rounded = local_time - datetime.timedelta(minutes=local_time.minute - 30)
    # The subtraction always produces a datetime with fold=0, which would
    # reinterpret an ambiguous local time (the repeated hour on the
    # clock-change day) as its first occurrence. Rounding stays inside the
    # same hour, so the original fold is still the right occurrence.
    if rounded.fold != local_time.fold:
        rounded = rounded.replace(fold=local_time.fold)
    return rounded


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
    # Start of the settlement period in local time. A settlement period is
    # half an hour of absolute time: on the clock-change days the wall clock
    # skips or repeats an hour, so the offset is added to the instant, not to
    # the wall time. pytz got that for free from its fixed-offset datetimes
    # plus normalize(); with zoneinfo we go through UTC instead.
    offset = datetime.timedelta(minutes=30 * (sp - 1))
    return (first_period_start.astimezone(datetime.timezone.utc) + offset).astimezone(
        first_period_start.tzinfo
    )


def convert_sp_and_date_to_utc(
    sp: int, date: datetime.date, timezone_str: str = GB_TZ, is_wholesale: bool = False
) -> datetime.datetime:
    """
    Return an UTC-aware datetime for the start of a given settlement period.
    """
    local_time = convert_sp_and_date_to_local(sp, date, timezone_str, is_wholesale)
    return _to_timezone(local_time, UTC_TZ).replace(tzinfo=datetime.timezone.utc)


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
    first_delivery_time = _get_first_delivery_time(
        delivery_date, timezone_str, is_wholesale
    )
    # Fetch settlement period. The two datetimes share the Europe/London
    # ZoneInfo instance, and a subtraction between datetimes with the same
    # tzinfo ignores that tzinfo (the wall-clock difference); a settlement
    # period is half an hour of absolute time, so compare the instants.
    delta = half_hourly_time.astimezone(
        datetime.timezone.utc
    ) - first_delivery_time.astimezone(datetime.timezone.utc)
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


def number_of_periods_in_timedelta(delta: datetime.timedelta) -> float:
    """
    Return the number of half-hourly settlement periods in the given timedelta
    """
    return (delta.total_seconds() / 60) / 30

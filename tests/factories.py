import datetime
from typing import Any, Callable

from dateutil import parser as date_parser
from dateutil import relativedelta
from django.utils import timezone

from xocto import localtime


class DateTimeFactory(object):
    """
    A class for generating datetimes in a certain timezone.
    """

    def __init__(
        self,
        str_to_dt_fn: Callable[[str], datetime.datetime],
        now_fn: Callable[[], datetime.datetime],
    ):
        self._str_to_dt_fn = str_to_dt_fn
        self._now_fn = now_fn

    def dt(self, dt_str: str) -> datetime.datetime:
        """
        Return a datetime from a string.
        """
        return self._str_to_dt_fn(dt_str)

    def now(self) -> datetime.datetime:
        return self._now_fn()

    def in_the_past(self, **kwargs: Any) -> datetime.datetime:
        if not kwargs:
            kwargs = {"days": 90}
        return self.now() - relativedelta.relativedelta(**kwargs)

    def in_the_future(self, **kwargs: Any) -> datetime.datetime:
        if not kwargs:
            kwargs = {"days": 90}
        return self.now() + relativedelta.relativedelta(**kwargs)

    def a_day_ago(self) -> datetime.datetime:
        return self.in_the_past(days=1)

    def a_day_later(self) -> datetime.datetime:
        return self.in_the_future(days=1)


def _utc_dt(value: str) -> datetime.datetime:
    """
    Return a UTC datetime from the passed string.

    Examples: datetime('31/5/2010') or datetime("Aug 28 1999 12:00AM")

    UK date format is assumed, so DD/MM/YYYY works as expected.
    """
    _datetime = date_parser.parse(value, dayfirst=("/" in value))
    return _datetime.replace(tzinfo=timezone.utc)


def _local_dt(value: str) -> datetime.datetime:
    """
    Return a LOCAL datetime from the passed string.
    """
    _datetime = date_parser.parse(value, dayfirst=("/" in value))
    return timezone.make_aware(_datetime)


utc = DateTimeFactory(str_to_dt_fn=_utc_dt, now_fn=timezone.now)
local = DateTimeFactory(str_to_dt_fn=_local_dt, now_fn=localtime.now)


def date(value: str) -> datetime.date:
    _datetime = date_parser.parse(value, dayfirst=("/" in value))
    return _datetime.date()


def time(_time: str) -> datetime.time:
    try:
        return datetime.datetime.strptime(_time, "%H:%M").time()
    except ValueError:
        return datetime.datetime.strptime(_time, "%H:%M:%S").time()

import datetime
import decimal
import zoneinfo

import pytest
import time_machine
from dateutil import relativedelta
from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from tests import factories
from xocto import localtime


class TestNow:
    def test_now_is_in_correct_timezone(self):
        now = localtime.now()
        assert str(now.tzinfo) == settings.TIME_ZONE


class TestSecondsInTheFuture:
    def test_seconds_in_future(self):
        with time_machine.travel("2020-01-01 12:00:00.000", tick=False):
            assert localtime.seconds_in_the_future(1) == localtime.as_localtime(
                localtime.datetime_.datetime(2020, 1, 1, 12, 0, 1, tzinfo=localtime.UTC)
            )
            assert localtime.seconds_in_the_future(1.5) == localtime.as_localtime(
                localtime.datetime_.datetime(
                    2020, 1, 1, 12, 0, 1, 500000, tzinfo=localtime.UTC
                )
            )


class TestSecondsInThePast:
    def test_seconds_in_past(self):
        with time_machine.travel("2020-01-01 12:00:00.000", tick=False):
            assert localtime.seconds_in_the_past(1) == localtime.as_localtime(
                localtime.datetime_.datetime(
                    2020, 1, 1, 11, 59, 59, tzinfo=localtime.UTC
                )
            )
            assert localtime.seconds_in_the_past(1.5) == localtime.as_localtime(
                localtime.datetime_.datetime(
                    2020, 1, 1, 11, 59, 58, 500000, tzinfo=localtime.UTC
                )
            )


class TestDate:
    def test_date_calculation_near_midnight_during_bst(self):
        near_midnight_in_utc = datetime.datetime(
            2016, 6, 1, 23, 50, 0, tzinfo=localtime.UTC
        )
        assert localtime.date(near_midnight_in_utc) == (
            near_midnight_in_utc.date() + datetime.timedelta(days=1)
        )

    def test_date_calculation_near_midnight_outside_of_bst(self):
        near_midnight_in_utc = datetime.datetime(
            2016, 11, 1, 23, 50, 0, tzinfo=localtime.UTC
        )
        assert localtime.date(near_midnight_in_utc) == near_midnight_in_utc.date()

    @pytest.mark.parametrize("tz", (zoneinfo.ZoneInfo("Etc/GMT-10"), localtime.UTC))
    def test_date_calculation_specifying_other_timezone(self, tz):
        near_midnight = datetime.datetime(2016, 6, 1, 23, 50, 0, tzinfo=tz)
        assert localtime.date(near_midnight, tz=tz) == (near_midnight.date())

    def test_datetime_not_supplied(self):
        """
        Check that we do not fallback to today if a datetime is not passed to the function -
        we have localtime.today for that.
        """
        with pytest.raises(
            TypeError, match="You must supply a datetime to localtime.date"
        ):
            localtime.date(None)


class TestDateOfDayBefore:
    @override_settings(TIME_ZONE="Europe/London")
    @pytest.mark.parametrize(
        "dt, date_of_day_before",
        [
            # Local time midnight: does what you'd expect
            (factories.local.dt("2019-06-01 00:00:00"), factories.date("2019-05-31")),
            # Note that this next example is *the same time*, but expressed in UTC. So again, it
            # correctly returns the same date. But you might not be expecting it when you see it.
            (factories.utc.dt("2019-05-31 23:00:00"), factories.date("2019-05-31")),
            # A couple of 'normal' examples
            (factories.local.dt("2019-01-23 05:30:00"), factories.date("2019-01-22")),
            (factories.utc.dt("2019-01-23 05:30:00"), factories.date("2019-01-22")),
        ],
    )
    def test_returns_expected_results(self, dt, date_of_day_before):
        assert localtime.date_of_day_before(dt) == date_of_day_before


class TestMidnight:
    def test_midnight_calculation_for_bst_date(self):
        date = datetime.date(2016, 7, 2)
        midnight = localtime.midnight(date)
        assert midnight.tzinfo is not None
        assert midnight.hour == 0

        midnight_utc = midnight.astimezone(localtime.UTC)
        assert midnight_utc.hour == 23

    def test_midnight_calculation_for_utc_dt(self):
        dt = factories.utc.dt("2017-12-20T16:00")

        assert localtime.midnight(dt) == localtime.datetime(2017, 12, 20, 0, 0)

    def test_midnight_calculation_without_date_uses_today(self):
        midnight = localtime.midnight()
        assert midnight.date() == localtime.today()
        assert midnight.tzinfo is not None
        assert midnight.hour == 0

    def test_convert_date_to_midnight_and_back(self):
        date = datetime.date(2016, 7, 2)
        midnight = localtime.midnight(date)
        midnight_utc = midnight.astimezone(localtime.UTC)
        assert localtime.date(midnight_utc) == date

    def test_midnight_in_different_timezone(self):
        aus_time = zoneinfo.ZoneInfo("Etc/GMT-10")

        with time_machine.travel(
            datetime.datetime(2020, 2, 2, 1, tzinfo=aus_time), tick=False
        ):
            result = localtime.midnight(tz=aus_time)

        assert result == datetime.datetime(2020, 2, 2, 0, 0, tzinfo=aus_time)

    def test_doesnt_change_date_of_already_midnight_datetime(self):
        """
        Check that if we pass a datetime to `midnight()` which is *already* midnight in the
        relevant timezone, it doesn't get changed.
        """
        midnight = datetime.datetime(2020, 6, 1, 23, tzinfo=datetime.timezone.utc)

        # We'll assert the same thing three ways for clarity:
        assert (
            localtime.midnight(midnight).date()
            == localtime.as_localtime(midnight).date()
        )
        assert localtime.midnight(midnight).date() == datetime.date(2020, 6, 2)
        assert localtime.midnight(midnight) == midnight

    @override_settings(
        TIME_ZONE="Australia/Sydney"
    )  # set the django default/current timezone
    @pytest.mark.parametrize(
        "naive_datetime,expected_midnight",
        [
            (
                datetime.datetime(2021, 6, 17, 18, 0, 0),
                datetime.datetime(2021, 6, 17, 0, 0, 0),
            ),
            (
                datetime.datetime(2021, 6, 17, 23, 30, 0),
                datetime.datetime(2021, 6, 17, 0, 0, 0),
            ),
            (
                datetime.datetime(2021, 6, 18, 0, 0, 0),
                datetime.datetime(2021, 6, 18, 0, 0, 0),
            ),
            (
                datetime.datetime(2021, 6, 18, 0, 30, 0),
                datetime.datetime(2021, 6, 18, 0, 0, 0),
            ),
            (
                datetime.datetime(2021, 6, 18, 6, 0, 0),
                datetime.datetime(2021, 6, 18, 0, 0, 0),
            ),
        ],
    )
    def test_localtime_midnight_calculation_for_naive_datetime_and_no_timezone(
        self, naive_datetime, expected_midnight
    ):
        """
        Test the behavior of localtime.midnight() when passed a naive datetime and NOT passed a tz

        We prefer to not pass a naive datetime to midnight(), but if you do,
        this is the behaviour with no tz argument:
        1. the naive datetime is assumed to be in the current Django timezone
        2. get the date of that datetime
        3. return midnight at the start of that date, in the current Django timezone.
        """
        # attach the current Sydney timezone to the expected midnight
        expected_midnight = timezone.make_aware(expected_midnight)

        actual_midnight = localtime.midnight(naive_datetime)

        assert actual_midnight == expected_midnight
        assert str(actual_midnight.tzinfo) == "Australia/Sydney"

    @override_settings(
        TIME_ZONE="Australia/Sydney"
    )  # set the django default/current timezone
    @pytest.mark.parametrize(
        "naive_datetime,specified_timezone,expected_midnight",
        [
            (
                # this is assumed to be in the current django timezone (Sydney)
                datetime.datetime(2021, 6, 17, 18, 0, 0),
                # then converted to UTC - moved 10 hours back - still same date
                "UTC",
                # result is midnight at start of the date
                datetime.datetime(2021, 6, 17, 0, 0, 0),
            ),
            (
                # this is assumed to be in the current django timezone (Sydney)
                datetime.datetime(2021, 6, 21, 5, 0, 0),
                # then converted to UTC - moved 10 hours back - changes to previous date
                "UTC",
                # midnight returned is previous date - this result can be unexpected
                datetime.datetime(2021, 6, 20, 0, 0, 0),
            ),
            (
                # this is assumed to be in the current django timezone (Sydney)
                datetime.datetime(2021, 6, 24, 23, 0, 0),
                # then converted to Pacific/Auckland - moved 2 hours ahead - changes to next date
                "Pacific/Auckland",
                # midnight returned is next date - this result can be unexpected
                datetime.datetime(2021, 6, 25, 0, 0, 0),
            ),
            (
                # This example was the cause of a bug in Australia:
                # this is assumed to be in the current django timezone (Sydney),
                # which on this date is UTC+11 (DST)
                datetime.datetime(2021, 2, 16, 0, 0, 0),
                # then converted to UTC+10 (the INDUSTRY_TIMEZONE in Australia)
                # which moves it 1 hour back - changes to previous date
                "Etc/GMT-10",
                # midnight returned is previous date - this result can be unexpected
                datetime.datetime(2021, 2, 15, 0, 0, 0),
            ),
            (
                # this is assumed to be in the current django timezone (Sydney),
                # which on this date is UTC+10
                datetime.datetime(2021, 7, 16, 0, 0, 0),
                # then converted to UTC+10 (the INDUSTRY_TIMEZONE in Australia)
                # no change - date is kept the same
                "Etc/GMT-10",
                # midnight returned is same date
                datetime.datetime(2021, 7, 16, 0, 0, 0),
            ),
        ],
    )
    def test_localtime_midnight_calculation_for_naive_datetime_and_specified_timezone(
        self, naive_datetime, specified_timezone, expected_midnight
    ):
        """
        Test the behavior of localtime.midnight() when passed a naive datetime and a timezone

        We prefer to not pass a naive datetime to midnight(), but if you do,
        this is the behaviour when tz argument is specified:
        1. the naive datetime is assumed to be in the current Django timezone
            (NOT the passed timezone)
        2. convert that moment in time to the specified timezone
        3. get the date of that datetime
        3. return midnight at the start of that date, in the specified timezone.
        """
        specified_timezone_obj = zoneinfo.ZoneInfo(specified_timezone)
        # attach the specified timezone to the expected midnight
        expected_midnight = timezone.make_aware(
            expected_midnight, timezone=specified_timezone_obj
        )

        actual_midnight = localtime.midnight(naive_datetime, tz=specified_timezone_obj)

        assert actual_midnight == expected_midnight
        assert str(actual_midnight.tzinfo) == specified_timezone


class TestMidday:
    def test_midday_calculation(self):
        date = datetime.date(2016, 7, 2)
        midday = localtime.midday(date)
        assert midday.tzinfo is not None
        assert midday.hour == 12
        assert midday.minute == 0

    def test_midday_calculation_without_date_uses_today(self):
        midday = localtime.midday()
        assert midday.date() == localtime.today()
        assert midday.tzinfo is not None
        assert midday.hour == 12
        assert midday.minute == 0

    def test_midday_in_different_timezone(self):
        aus_time = zoneinfo.ZoneInfo("Etc/GMT-10")

        with time_machine.travel(
            datetime.datetime(2020, 2, 2, 1, tzinfo=aus_time), tick=False
        ):
            result = localtime.midday(tz=aus_time)

        assert result == datetime.datetime(2020, 2, 2, 12, 0, tzinfo=aus_time)


class TestLatest:
    def test_latest_calculation(self):
        date = datetime.date(2016, 7, 2)
        latest = localtime.latest(date)
        assert latest.tzinfo is not None
        assert latest.hour == 23
        assert latest.minute == 59
        assert latest.second == 59
        assert latest.microsecond == 999999

    def test_latest_calculation_without_date_uses_today(self):
        latest = localtime.latest()
        assert latest.date() == localtime.today()
        assert latest.tzinfo is not None
        assert latest.hour == 23
        assert latest.minute == 59
        assert latest.second == 59
        assert latest.microsecond == 999999


class TestDateTime:
    def test_datetime_creation(self):
        dt = localtime.datetime(2016, 8, 5)
        assert dt.hour == 0
        utc_dt = dt.astimezone(localtime.UTC)
        assert utc_dt.hour == 23

    def test_dst_ambiguity(self):
        # 2020-10-25T01:30 is an ambiguous dt in Europe/London as its in the period when clocks go
        # back (so it occurs twice).
        dt = localtime.datetime(2020, 10, 25, 1, 30)
        assert dt.hour == 1
        assert dt.minute == 30
        assert dt.dst() == datetime.timedelta(seconds=3600)
        utc_dt = dt.astimezone(localtime.UTC)
        assert utc_dt.hour == 0


class TestAsLocaltime:
    def test_conversion_of_gmt_dt(self):
        non_dst_datetime = datetime.datetime(2016, 1, 1, 23, 1, tzinfo=localtime.UTC)
        converted_non_dst_datetime = localtime.as_localtime(non_dst_datetime)

        # The two dates are 'equal' and their day and hour attributes differ
        assert converted_non_dst_datetime == non_dst_datetime
        assert converted_non_dst_datetime.day == non_dst_datetime.day
        assert converted_non_dst_datetime.hour == non_dst_datetime.hour

    def test_conversion_of_bst_dt(self):
        dst_datetime = datetime.datetime(2016, 5, 1, 23, 1, tzinfo=localtime.UTC)
        converted_dst_datetime = localtime.as_localtime(dst_datetime)

        # The two dates are 'equal' but their day and hour attributes differ
        assert converted_dst_datetime == dst_datetime
        assert converted_dst_datetime.day == dst_datetime.day + 1
        assert converted_dst_datetime.hour == dst_datetime.hour - 23

    def test_converts_utc_to_europe_london(self):
        utc_dt = factories.utc.dt("2018-05-28T23:30")
        assert str(utc_dt.tzinfo) == "UTC"

        local_dt = localtime.as_localtime(utc_dt)
        assert str(local_dt.tzinfo) == "Europe/London"


class TestIsUTC:
    @pytest.mark.parametrize("tzinfo", [datetime.timezone.utc, localtime.UTC])
    def test_is_utc(self, tzinfo):
        now = datetime.datetime(2020, 1, 1, tzinfo=tzinfo)
        assert localtime.is_utc(now)

    def test_is_not_utc(self):
        now = datetime.datetime(2020, 1, 1, tzinfo=localtime.LONDON)
        assert not localtime.is_utc(now)


class TestIsLocalime:
    def test_is_local_time(self):
        assert localtime.is_local_time(localtime.now())

    def test_is_not_local_time(self):
        dt = datetime.datetime(2016, 8, 5, tzinfo=datetime.timezone.utc)
        assert not localtime.is_local_time(dt)


class TestQuantise:
    @pytest.mark.parametrize(
        ("dt", "timedelta", "rounding_strategy", "result"),
        [
            (
                localtime.datetime(2016, 12, 5, 11, 34, 59),
                datetime.timedelta(minutes=30),
                None,
                localtime.datetime(2016, 12, 5, 11, 30, 0),
            ),
            (
                localtime.datetime(2016, 12, 5, 11, 29, 59),
                datetime.timedelta(minutes=30),
                None,
                localtime.datetime(2016, 12, 5, 11, 30, 0),
            ),
            (
                localtime.datetime(2016, 12, 5, 11, 14, 59),
                datetime.timedelta(minutes=30),
                None,
                localtime.datetime(2016, 12, 5, 11, 0, 0),
            ),
            (
                localtime.datetime(2016, 12, 5, 11, 15, 59),
                datetime.timedelta(minutes=30),
                None,
                localtime.datetime(2016, 12, 5, 11, 30, 0),
            ),
            (
                localtime.datetime(2016, 12, 5, 11, 16, 0),
                datetime.timedelta(minutes=30),
                None,
                localtime.datetime(2016, 12, 5, 11, 30, 0),
            ),
            (
                localtime.datetime(2016, 12, 5, 10, 59, 59),
                datetime.timedelta(hours=2),
                None,
                localtime.datetime(2016, 12, 5, 10, 0, 0),
            ),
            (
                localtime.datetime(2016, 12, 5, 11, 0, 0),
                datetime.timedelta(hours=2),
                None,
                localtime.datetime(2016, 12, 5, 12, 0, 0),
            ),
            (
                localtime.datetime(2016, 12, 31, 13, 34, 59),
                datetime.timedelta(hours=24),
                None,
                localtime.datetime(2017, 1, 1, 0, 0, 0),
            ),
            (
                localtime.datetime(2016, 12, 31, 0, 0, 1),
                datetime.timedelta(days=1),
                None,
                localtime.datetime(2016, 12, 31, 0, 0, 0),
            ),
            # CUSTOM ROUNDING STRATEGIES
            (
                localtime.datetime(2016, 2, 2, 12, 30, 1),
                datetime.timedelta(minutes=30),
                decimal.ROUND_UP,
                localtime.datetime(2016, 2, 2, 13, 0, 0),
            ),
            (
                localtime.datetime(2016, 2, 2, 12, 45, 0),
                datetime.timedelta(minutes=30),
                decimal.ROUND_HALF_UP,
                localtime.datetime(2016, 2, 2, 13, 0, 0),
            ),
            (
                localtime.datetime(2016, 2, 2, 12, 45, 0),
                datetime.timedelta(minutes=30),
                decimal.ROUND_HALF_DOWN,
                localtime.datetime(2016, 2, 2, 12, 30, 0),
            ),
            (
                localtime.datetime(2016, 2, 2, 12, 0, 0),
                datetime.timedelta(days=1),
                decimal.ROUND_HALF_DOWN,
                localtime.datetime(2016, 2, 2, 0, 0, 0),
            ),
            (
                localtime.datetime(2016, 2, 2, 22, 0),
                datetime.timedelta(days=1),
                decimal.ROUND_HALF_UP,
                localtime.datetime(2016, 2, 3, 0, 0, 0),
            ),
            # Test doesn't round beyond limits
            (
                localtime.datetime(2016, 2, 2, 12, 30, 0),
                datetime.timedelta(minutes=30),
                decimal.ROUND_UP,
                localtime.datetime(2016, 2, 2, 12, 30, 0),
            ),
            (
                localtime.datetime(2016, 2, 2, 12, 30, 0),
                datetime.timedelta(minutes=30),
                decimal.ROUND_DOWN,
                localtime.datetime(2016, 2, 2, 12, 30, 0),
            ),
        ],
    )
    def test_quantise(self, dt, timedelta, rounding_strategy, result):
        args = (dt, timedelta)
        kwargs = dict(rounding=rounding_strategy) if rounding_strategy else {}
        assert localtime.quantise(*args, **kwargs) == result


class TestDateBoundaries:
    def test_date_boundaries_for_gmt_date(self):
        date = datetime.date(2017, 1, 1)

        start, end = localtime.date_boundaries(date)

        assert localtime.is_local_time(start)
        assert localtime.is_local_time(end)
        assert (end - start) == datetime.timedelta(days=1)
        assert localtime.datetime(2017, 1, 1) == start
        assert localtime.datetime(2017, 1, 2) == end

    def test_date_boundaries_for_bst_date(self):
        date = datetime.date(2017, 5, 1)

        start, end = localtime.date_boundaries(date)

        assert localtime.is_local_time(start)
        assert localtime.is_local_time(end)
        assert (end - start) == datetime.timedelta(days=1)
        assert localtime.datetime(2017, 5, 1) == start
        assert localtime.datetime(2017, 5, 2) == end

    def test_date_boundaries_for_spring_dst_boundary(self):
        date = datetime.date(2017, 3, 26)

        start, end = localtime.date_boundaries(date)

        assert localtime.is_local_time(start)
        assert localtime.is_local_time(end)
        delta = datetime.timedelta(seconds=(end.timestamp() - start.timestamp()))
        assert delta == datetime.timedelta(seconds=23 * 60 * 60)
        assert localtime.datetime(2017, 3, 26) == start
        assert localtime.datetime(2017, 3, 27) == end

    def test_date_boundaries_for_autumn_dst_boundary(self):
        date = datetime.date(2017, 10, 29)

        start, end = localtime.date_boundaries(date)

        assert localtime.is_local_time(start)
        assert localtime.is_local_time(end)
        delta = datetime.timedelta(seconds=(end.timestamp() - start.timestamp()))
        assert delta == datetime.timedelta(seconds=25 * 60 * 60)
        assert localtime.datetime(2017, 10, 29) == start
        assert localtime.datetime(2017, 10, 30) == end


class TestMonthBoundaries:
    def test_march_2021(self):
        assert localtime.month_boundaries(month=3, year=2021) == (
            factories.local.dt("2021-03-01T00:00"),
            factories.local.dt("2021-04-01T00:00"),
        )


class TestStartOfMonth:
    @pytest.mark.parametrize(
        ("dt", "result"),
        [
            (
                localtime.datetime(2016, 12, 5, 11, 34, 59),
                localtime.datetime(2016, 12, 1, 0, 0, 0),
            ),
            (
                localtime.datetime(2017, 3, 31, 11, 29, 59),
                localtime.datetime(2017, 3, 1, 0, 0, 0),
            ),
        ],
    )
    def test_start_of_month(self, dt, result):
        assert localtime.start_of_month(dt) == result


class TestEndOfMonth:
    @pytest.mark.parametrize(
        ("dt", "result"),
        [
            (
                localtime.datetime(2016, 12, 5, 11, 34, 59),
                localtime.datetime(2017, 1, 1, 0, 0, 0),
            ),
            (
                localtime.datetime(2017, 3, 31, 11, 29, 59),
                localtime.datetime(2017, 4, 1, 0, 0, 0),
            ),
        ],
    )
    def test_end_of_month(self, dt, result):
        assert localtime.end_of_month(dt) == result


class TestAsRange:
    def test_converts_date_to_correct_values(self):
        min_dt, max_dt = localtime.as_range(factories.date("2017-10-01"))

        assert localtime.is_local_time(min_dt)
        assert min_dt == localtime.datetime(2017, 10, 1)

        assert localtime.is_local_time(max_dt)
        assert max_dt == localtime.datetime(2017, 10, 1, 23, 59, 59, 999999)


class TestIsInFutureOrPast:
    def test_with_aware_datetimes(self):
        dt1 = factories.utc.in_the_future(minutes=5), True
        dt2 = factories.utc.in_the_past(minutes=10), False
        dt3 = factories.utc.in_the_future(days=20), True
        dt4 = factories.utc.in_the_past(months=1), False
        for dt, in_future in (dt1, dt2, dt3, dt4):
            assert localtime.is_in_the_future(dt) is in_future
            assert localtime.is_in_the_past(dt) is not in_future

    def test_with_naive_datetimes(self):
        dt = datetime.datetime.now()
        with pytest.raises(ValueError):
            localtime.is_in_the_past(dt)


class TestNextMidnight:
    def test_utc_date(self):
        dt = localtime.next_midnight(factories.date("2017-01-01"))

        assert str(dt.tzinfo) == "Europe/London"
        assert dt == localtime.datetime(2017, 1, 2)

    def test_dst_start(self):
        dt = localtime.next_midnight(factories.date("2018-03-25"))

        assert str(dt.tzinfo) == "Europe/London"
        assert dt == localtime.datetime(2018, 3, 26)

    def test_dst_end(self):
        dt = localtime.next_midnight(factories.date("2018-10-28"))

        assert str(dt.tzinfo) == "Europe/London"
        assert dt == localtime.datetime(2018, 10, 29)

    def test_default_in_different_timezone(self):
        aus_time = zoneinfo.ZoneInfo("Etc/GMT-10")

        with time_machine.travel(
            datetime.datetime(2020, 2, 2, 1, tzinfo=aus_time), tick=False
        ):
            result = localtime.next_midnight(tz=aus_time)

        assert result == datetime.datetime(2020, 2, 3, 0, 0, tzinfo=aus_time)

    @pytest.mark.parametrize(
        "dt,expected",
        [
            # GMT -> BST
            (localtime.datetime(2018, 3, 24), localtime.datetime(2018, 3, 25)),
            (localtime.datetime(2018, 3, 25), localtime.datetime(2018, 3, 26)),
            (localtime.datetime(2018, 3, 26), localtime.datetime(2018, 3, 27)),
            # BST -> GMT
            (localtime.datetime(2018, 10, 27), localtime.datetime(2018, 10, 28)),
            (localtime.datetime(2018, 10, 28), localtime.datetime(2018, 10, 29)),
            (localtime.datetime(2018, 10, 29), localtime.datetime(2018, 10, 30)),
        ],
    )
    def test_dst_end_datetime(self, dt, expected):
        result = localtime.next_midnight(dt)

        assert result == expected
        assert str(result.tzinfo) == "Europe/London"


class TestDaysInThePast:
    def test_is_sane(self):
        assert localtime.days_in_the_past(
            2
        ) == datetime.date.today() - datetime.timedelta(days=2)
        assert localtime.days_in_the_past(
            -20
        ) == datetime.date.today() + datetime.timedelta(days=20)
        assert localtime.days_in_the_past(0) == datetime.date.today()
        assert localtime.days_in_the_past(1) == localtime.yesterday()
        assert localtime.days_in_the_past(-1) == localtime.tomorrow()


class TestDaysInTheFuture:
    def test_is_sane(self):
        assert localtime.days_in_the_future(
            2
        ) == datetime.date.today() + datetime.timedelta(days=2)
        assert localtime.days_in_the_future(
            -20
        ) == datetime.date.today() - datetime.timedelta(days=20)
        assert localtime.days_in_the_future(0) == datetime.date.today()
        assert localtime.days_in_the_future(1) == localtime.tomorrow()
        assert localtime.days_in_the_future(-1) == localtime.yesterday()


class TestLatestDateForDay:
    @pytest.mark.parametrize(
        "start_date,end_date,day_of_month,expected_result",
        (
            ("2017-01-01", "2018-12-31", 9, "2018-12-09"),  # Result in last month.
            ("2017-01-01", "2018-12-08", 9, "2018-11-09"),  # Result in previous month.
            (
                "2017-01-01",
                "2017-03-30",
                31,
                "2017-01-31",
            ),  # Result affected by short month.
            ("2017-01-12", "2017-01-30", 12, "2017-01-12"),  # Result same as from date.
            ("2017-01-12", "2017-01-30", 30, "2017-01-30"),  # Result same as to date.
            ("2017-01-12", "2017-02-10", 11, None),  # Result not in range.
            ("2017-01-01", "2016-01-01", 1, ValueError),  # Invalid range.
            ("2017-01-01", "2018-12-31", 0, ValueError),  # Day too low.
            ("2017-01-01", "2018-12-31", 32, ValueError),  # Day too high.
        ),
    )
    def test_latest_date_for_day(
        self, start_date, end_date, day_of_month, expected_result
    ):
        kwargs = dict(
            start_date=factories.date(start_date),
            end_date=factories.date(end_date),
            day_of_month=day_of_month,
        )
        if isinstance(expected_result, type) and issubclass(expected_result, Exception):
            with pytest.raises(expected_result):
                localtime.latest_date_for_day(**kwargs)
        else:
            if expected_result is not None:
                expected_result = factories.date(expected_result)

            result = localtime.latest_date_for_day(**kwargs)
            assert result == expected_result


class TestIsWithinTheLastYear:
    @pytest.mark.parametrize(
        "now_string, supplied_date_string, within_last_year",
        [
            # Same day should be True:
            ("2019-01-01 00:00:00", "2019-01-01", True),  # Midnight GMT
            ("2019-08-01 00:00:00", "2019-08-01", True),  # Midnight BST
            ("2019-01-01 23:59:59", "2019-01-01", True),  # Just before midnight GMT
            ("2019-08-01 23:59:59", "2019-08-01", True),  # Just after midnight BST
            # Tomorrow should be False:
            ("2019-01-01 00:00:00", "2019-01-02", False),  # Midnight GMT
            ("2019-08-01 00:00:00", "2019-08-02", False),  # Midnight BST
            ("2019-01-01 23:59:59", "2019-01-02", False),  # Just before midnight GMT
            ("2019-08-01 23:59:59", "2019-08-02", False),  # Just after midnight BST
            # Exactly a year ago should be True:
            ("2019-01-01 00:00:00", "2018-01-01", True),  # Midnight GMT
            ("2019-08-01 00:00:00", "2018-08-01", True),  # Midnight BST
            ("2019-01-01 23:59:59", "2018-01-01", True),  # Just before midnight GMT
            ("2019-08-01 23:59:59", "2018-08-01", True),  # Just after midnight BST
            # A year and a day ago should be False:
            ("2019-01-01 00:00:00", "2017-12-31", False),  # Midnight GMT
            ("2019-08-01 00:00:00", "2018-07-31", False),  # Midnight BST
            ("2019-01-01 23:59:59", "2017-12-31", False),  # Just before midnight GMT
            ("2019-08-01 23:59:59", "2018-07-31", False),  # Just after midnight BST
            # Leap years (2020 is a leap year):
            ("2019-02-28 12:00:00", "2018-02-28", True),
            ("2019-02-28 12:00:00", "2018-02-27", False),
            ("2020-02-29 12:00:00", "2019-02-28", True),
            ("2020-02-29 12:00:00", "2019-02-27", False),
            ("2021-02-28 12:00:00", "2020-02-28", True),
            ("2021-02-28 12:00:00", "2020-02-27", False),
        ],
    )
    def test_returns_correct_results_for_dates(
        self, now_string, supplied_date_string, within_last_year
    ):
        now = factories.local.dt(now_string)
        supplied_date = factories.date(supplied_date_string)
        with time_machine.travel(now, tick=False):
            assert localtime.is_within_the_last_year(supplied_date) == within_last_year


class TestWithinLastWeek:
    @pytest.mark.parametrize(
        "now_str, supplied_date_str, is_within_last_year",
        [
            # Same day should be True:
            ("2019-01-01 00:00:00", "2019-01-01", True),  # Midnight
            ("2019-01-01 23:59:59", "2019-01-01", True),  # Just before midnight
            # Tomorrow should be False:
            ("2019-01-01 00:00:00", "2019-01-02", False),  # Midnight
            ("2019-01-01 23:59:59", "2019-01-02", False),  # Just before midnight
            # Exactly a week ago should be True:
            ("2019-01-01 00:00:00", "2018-12-25", True),  # Midnight
            ("2019-01-01 23:59:59", "2018-12-25", True),  # Just before midnight
            # A week and a day ago should be False:
            ("2019-01-01 00:00:00", "2018-12-24", False),  # Midnight
            ("2019-01-01 23:59:59", "2018-12-24", False),  # Just before midnight
        ],
    )
    def test_returns_correct_results_for_dates(
        self, now_str, supplied_date_str, is_within_last_year
    ):
        now = factories.local.dt(now_str)
        supplied_date = factories.date(supplied_date_str)
        with time_machine.travel(now, tick=False):
            assert (
                localtime.is_within_the_last_week(supplied_date) == is_within_last_year
            )


class TestIsDST:
    @pytest.mark.parametrize(
        "naive_datetime,tz,expected",
        (
            # Test London timezone
            (datetime.datetime(2019, 1, 1), zoneinfo.ZoneInfo("Europe/London"), False),
            (datetime.datetime(2019, 6, 1), zoneinfo.ZoneInfo("Europe/London"), True),
            # Test London boundaries
            (
                datetime.datetime(2017, 3, 26, 0, 0),
                zoneinfo.ZoneInfo("Europe/London"),
                False,
            ),
            (
                datetime.datetime(2017, 3, 26, 2, 0),
                zoneinfo.ZoneInfo("Europe/London"),
                True,
            ),
            (
                datetime.datetime(2017, 10, 29, 0, 0),
                zoneinfo.ZoneInfo("Europe/London"),
                True,
            ),
            (
                datetime.datetime(2017, 10, 29, 2, 0),
                zoneinfo.ZoneInfo("Europe/London"),
                False,
            ),
            # UTC should never be DST
            (datetime.datetime(2019, 1, 1), zoneinfo.ZoneInfo("UTC"), False),
            (datetime.datetime(2019, 6, 1), zoneinfo.ZoneInfo("UTC"), False),
            (datetime.datetime(2019, 1, 1), datetime.timezone.utc, False),
            (datetime.datetime(2019, 6, 1), datetime.timezone.utc, False),
            # Test Eastern Australia timezone
            (
                datetime.datetime(2019, 1, 1),
                zoneinfo.ZoneInfo("Australia/Sydney"),
                True,
            ),
            (
                datetime.datetime(2019, 6, 1),
                zoneinfo.ZoneInfo("Australia/Sydney"),
                False,
            ),
            # Test Western Australia timezone (they don't have DST)
            (
                datetime.datetime(2019, 1, 1),
                zoneinfo.ZoneInfo("Australia/Perth"),
                False,
            ),
            (
                datetime.datetime(2019, 6, 1),
                zoneinfo.ZoneInfo("Australia/Perth"),
                False,
            ),
        ),
    )
    def test_returns_correct_values(self, naive_datetime, tz, expected):
        local_dt = timezone.make_aware(naive_datetime, timezone=tz)
        assert localtime.is_dst(local_dt) == expected

    def test_raises_value_error_for_naive_dt(self):
        with pytest.raises(ValueError):
            localtime.is_dst(datetime.datetime(2008, 4, 5))


class TestIsLocaltimeMidnight:
    @pytest.mark.parametrize(
        "dt",
        [
            # Valid datetimes in UTC and local, summer and winter.
            factories.local.dt("2019-12-01 00:00"),
            factories.utc.dt("2019-12-01 00:00"),
            factories.local.dt("2019-06-01 00:00"),
            factories.utc.dt("2019-06-01 23:00"),
        ],
    )
    def test_returns_true_for_localtime_midnights(self, dt):
        assert localtime.is_localtime_midnight(dt)

    @pytest.mark.parametrize(
        "dt",
        [
            factories.local.dt("2019-12-01 12:01"),
            factories.utc.dt("2019-12-01 12:01"),
            factories.local.dt("2019-06-01 12:01"),
            factories.utc.dt("2019-06-01 00:00"),
        ],
    )
    def test_returns_false_for_non_localtime_midnights(self, dt):
        assert not localtime.is_localtime_midnight(dt)

    def test_returns_false_if_timezone_differs(self):
        assert not localtime.is_localtime_midnight(
            factories.utc.dt("2020-12-01 00:00"),
            tz=zoneinfo.ZoneInfo("Europe/Paris"),
        )


class TestCombine:
    @pytest.mark.parametrize(
        "date, time, tz_name, expected",
        (
            (
                factories.date("1 Jan 2020"),
                factories.time("00:00"),
                "UTC",
                datetime.datetime(2020, 1, 1, tzinfo=localtime.UTC),
            ),
            (
                factories.date("1 Jan 2020"),
                factories.time("00:00"),
                "UTC",
                datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
            ),
            (
                factories.date("1 Jun 2020"),
                factories.time("01:00"),
                "Europe/London",
                datetime.datetime(2020, 6, 1, 1, 0).astimezone(
                    zoneinfo.ZoneInfo("Europe/London")
                ),
            ),
            (
                factories.date("1 Jul 2021"),
                factories.time("02:30"),
                "Europe/London",
                datetime.datetime(2021, 7, 1, 2, 30).astimezone(
                    zoneinfo.ZoneInfo("Europe/London")
                ),
            ),
        ),
    )
    def test_combines_as_expected(self, date, time, tz_name, expected):
        tz = zoneinfo.ZoneInfo(tz_name)
        assert localtime.combine(date, time, tz) == expected


class TestNextDateWithDayOfMonth:
    @pytest.mark.parametrize(
        "current_date, day_of_month, expected",
        (
            (factories.date("1 Jan 2020"), 1, factories.date("1 Feb 2020")),
            (factories.date("28 Jan 2020"), 1, factories.date("1 Feb 2020")),
            (factories.date("31 Jan 2020"), 31, factories.date("29 Feb 2020")),
            (factories.date("31 Dec 2019"), 2, factories.date("2 Jan 2020")),
        ),
    )
    def test_next_date_with_day_of_month(self, current_date, day_of_month, expected):
        assert (
            localtime.next_date_with_day_of_month(
                date=current_date, day_of_month=day_of_month
            )
            == expected
        )

    def test_raises_if_datetime_is_used(self):
        date_time = factories.utc.dt("1 Jan 2020 15:00")

        with pytest.raises(TypeError):
            localtime.next_date_with_day_of_month(date_time, 1)


class TestConsolidateIntoIntervals:
    def test_invalid_input(self):
        with pytest.raises(ValueError):
            localtime.consolidate_into_intervals([])

    @pytest.mark.parametrize(
        "dates_passed,dates_expected",
        [
            (
                [localtime.today()],
                [(localtime.today(), localtime.today())],
            ),
            (
                [
                    localtime.today(),
                    localtime.yesterday(),
                    localtime.days_in_the_future(2),
                ],
                [
                    (localtime.yesterday(), localtime.today()),
                    (localtime.days_in_the_future(2), localtime.days_in_the_future(2)),
                ],
            ),
        ],
    )
    def test_valid_input(self, dates_passed, dates_expected):
        assert localtime.consolidate_into_intervals(dates_passed) == dates_expected


class TestDatetimeFromUTCUnixTimestamp:
    @override_settings(TIME_ZONE="Europe/London")
    def test_timestamp_in_london_timezone(self):
        timestamp = 1605804900
        dt = localtime.datetime_from_epoch_timestamp(timestamp)
        assert dt == localtime.datetime(2020, 11, 19, 16, 55)

    @override_settings(TIME_ZONE="Etc/GMT-10")
    def test_timestamp_in_aus_timezone(self):
        timestamp = 1605804900
        dt = localtime.datetime_from_epoch_timestamp(timestamp)
        assert dt == localtime.datetime(2020, 11, 20, 2, 55)

    def test_timestamp_with_timestamp_argument(self):
        aus_time = zoneinfo.ZoneInfo("Etc/GMT-10")
        timestamp = 1605804900

        dt = localtime.datetime_from_epoch_timestamp(timestamp, tz=aus_time)
        assert dt == datetime.datetime(2020, 11, 20, 2, 55, tzinfo=aus_time)

    @override_settings(TIME_ZONE="Europe/London")
    def test_timestamp_british_summer_time_before_clocks_move_forward(self):
        """
        On the 29th of March 2020 at 1:00 am Europe/London = 1:00 am UTC
        the clocks move forward by an hour.
        That means that the clocks read 2:00 am at that point.
        """
        # Before clocks move forward
        # 29th of March 2020 0:30am UTC = 0:30am Europe/London
        timestamp = datetime.datetime(
            2020, 3, 29, 0, 30, tzinfo=localtime.UTC
        ).timestamp()

        dt = localtime.datetime_from_epoch_timestamp(timestamp)

        # Before daylight savings the time should be 0:30am (same as UTC)
        assert not localtime.is_dst(dt)
        assert dt.year == 2020
        assert dt.month == 3
        assert dt.day == 29
        assert dt.hour == 0
        assert dt.minute == 30

    @override_settings(TIME_ZONE="Europe/London")
    def test_timestamp_british_summer_time_after_clocks_move_forward(self):
        """
        On the 29th of March 2020 at 1:00 am Europe/London = 1:00 am UTC
        the clocks move forward by an hour.
        That means that the clocks read 2:00 am at that point.
        """
        # After clocks move forward
        # 29th of March 2020 1:30am UTC = 2:30 am Europe/London
        timestamp = datetime.datetime(
            2020, 3, 29, 1, 30, tzinfo=localtime.UTC
        ).timestamp()

        dt = localtime.datetime_from_epoch_timestamp(timestamp)

        # During daylight savings the time should be 2:30am (one hour forward)
        assert localtime.is_dst(dt)
        assert dt.year == 2020
        assert dt.month == 3
        assert dt.day == 29
        assert dt.hour == 2
        assert dt.minute == 30

    @override_settings(TIME_ZONE="Europe/London")
    def test_timestamp_british_summer_time_before_clocks_move_backward(self):
        """
        On the 25th of October 2020 at 2:00 am Europe/London = 1:00 am UTC
        the clocks move backwards by an hour.
        That means that the clocks read 1:00 am at that point.
        """
        # Before clocks move backwards
        # 25th of October 2020 0:30am UTC = 1:30am Europe/London
        timestamp = datetime.datetime(
            2020, 10, 25, 0, 30, tzinfo=localtime.UTC
        ).timestamp()

        dt = localtime.datetime_from_epoch_timestamp(timestamp)

        # During daylight savings the time should be 1:30am (one hour forward)
        assert localtime.is_dst(dt)
        assert dt.year == 2020
        assert dt.month == 10
        assert dt.day == 25
        assert dt.hour == 1
        assert dt.minute == 30

    @override_settings(TIME_ZONE="Europe/London")
    def test_timestamp_british_summer_time_after_clocks_move_backward(self):
        """
        On the 25th of October 2020 at 2:00 am Europe/London = 1:00 am UTC
        the clocks move backwards by an hour.
        That means that the clocks read 1:00 am at that point.
        """
        # After clocks move backwards
        # 25th of October 2020 1:30am UTC = 1:30am Europe/London
        timestamp = datetime.datetime(
            2020, 10, 25, 1, 30, tzinfo=localtime.UTC
        ).timestamp()

        dt = localtime.datetime_from_epoch_timestamp(timestamp)

        # After daylight savings ends the time should be 1:30am (same as UTC)
        assert not localtime.is_dst(dt)
        assert dt.year == 2020
        assert dt.month == 10
        assert dt.day == 25
        assert dt.hour == 1
        assert dt.minute == 30


class TestPeriodExceedsOneYear:
    @pytest.mark.parametrize(
        ("period_start_at", "first_dt_exceeding_one_year"),
        [
            (
                # Basic case.
                localtime.datetime(2021, 1, 1),
                localtime.datetime(2022, 1, 1, microsecond=1),
            ),
            (
                # A leap year.
                localtime.datetime(2020, 1, 1),
                localtime.datetime(2021, 1, 1, microsecond=1),
            ),
            (
                # Start on a leap year, Feb 28th.
                localtime.datetime(2020, 2, 28),
                localtime.datetime(2021, 2, 28, microsecond=1),
            ),
            (
                # Start on a leap year, Feb 29th.
                localtime.datetime(2020, 2, 29),
                localtime.datetime(2021, 3, 1, microsecond=1),  # !important
            ),
            (
                # Start on a leap year, March 1st.
                localtime.datetime(2020, 3, 1),
                localtime.datetime(2021, 3, 1, microsecond=1),
            ),
            (
                # End on a leap year, Feb 28th.
                localtime.datetime(2019, 2, 28),
                localtime.datetime(2020, 2, 28, microsecond=1),
            ),
            (
                # End on a leap year, March 1st.
                localtime.datetime(2019, 3, 1),
                localtime.datetime(2020, 3, 1, microsecond=1),
            ),
            (
                # Clock moves backward twice.
                localtime.datetime(2021, 10, 31),
                localtime.datetime(2022, 10, 31, microsecond=1),
            ),
            (
                # Clock moves forward twice.
                localtime.datetime(2021, 3, 28),
                localtime.datetime(2022, 3, 28, microsecond=1),
            ),
        ],
    )
    def test_period_exceeds_one_year(
        self, period_start_at, first_dt_exceeding_one_year
    ):
        assert localtime.period_exceeds_one_year(
            period_start_at, first_dt_exceeding_one_year
        )
        assert not localtime.period_exceeds_one_year(
            period_start_at,
            first_dt_exceeding_one_year - relativedelta.relativedelta(microseconds=1),
        )


class TestParseDate:
    def test_returns_date(self):
        assert localtime.parse_date("2020-01-01") == datetime.date(2020, 1, 1)

    def test_errors_if_invalid(self):
        with pytest.raises(ValueError) as exc_info:
            localtime.parse_date("abcd")

        assert "Invalid isoformat string" in str(exc_info.value)


class TestParseDatetime:
    @override_settings(TIME_ZONE="Australia/Sydney")
    def test_returns_datetime(self):
        assert localtime.parse_dt("2020-01-01 10:11:12") == datetime.datetime(
            2020, 1, 1, 10, 11, 12, tzinfo=zoneinfo.ZoneInfo("Australia/Sydney")
        )

    @override_settings(TIME_ZONE="Australia/Sydney")
    def test_assumes_midnight(self):
        assert localtime.parse_dt("2020-01-01") == datetime.datetime(
            2020, 1, 1, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo("Australia/Sydney")
        )

    def test_errors_if_timezone_specified(self):
        with pytest.raises(ValueError) as exc_info:
            localtime.parse_dt("2020-01-01 10:11 +01:00")

        assert "expects a naive datetime" in str(exc_info.value)

    def test_errors_if_invalid(self):
        with pytest.raises(ValueError) as exc_info:
            localtime.parse_date("abcd")

        assert "Invalid isoformat string" in str(exc_info.value)


class TestStrftime:
    @override_settings(TIME_ZONE="Europe/Berlin")
    def test_formats_datetime_in_local_timezone(self):
        dt = datetime.datetime(2023, 10, 1, 22, 30, 0, tzinfo=timezone.utc)
        fmt = "%Y-%m-%d %H:%M:%S %z"

        assert localtime.strftime(dt, fmt) == "2023-10-02 00:30:00 +0200"
        assert (
            localtime.strftime(dt, fmt, tz=zoneinfo.ZoneInfo("Europe/London"))
            == "2023-10-01 23:30:00 +0100"
        )

import datetime

import pytest
import pytz

from xocto import settlement_periods


UTC_TZ = datetime.timezone.utc
GB_TZ = pytz.timezone("Europe/London")


@pytest.mark.parametrize(
    "sp,date,expected",
    [
        # British time is GMT
        (
            1,
            datetime.date(2017, 1, 1),
            datetime.datetime(2016, 12, 31, hour=23, tzinfo=UTC_TZ),
        ),
        (
            48,
            datetime.date(2017, 1, 1),
            datetime.datetime(2017, 1, 1, hour=22, minute=30, tzinfo=UTC_TZ),
        ),
        # British time is GMT
        (
            1,
            datetime.date(2017, 7, 1),
            datetime.datetime(2017, 6, 30, hour=22, tzinfo=UTC_TZ),
        ),
        (
            48,
            datetime.date(2017, 7, 1),
            datetime.datetime(2017, 7, 1, hour=21, minute=30, tzinfo=UTC_TZ),
        ),
        # Change clock forward day, from GMT to BST
        (
            3,
            datetime.date(2017, 3, 26),
            datetime.datetime(2017, 3, 26, hour=0, tzinfo=UTC_TZ),
        ),
        (
            5,
            datetime.date(2017, 3, 26),
            datetime.datetime(2017, 3, 26, hour=1, tzinfo=UTC_TZ),
        ),
        (
            7,
            datetime.date(2017, 3, 26),
            datetime.datetime(2017, 3, 26, hour=2, tzinfo=UTC_TZ),
        ),
        (
            45,
            datetime.date(2017, 3, 26),
            datetime.datetime(2017, 3, 26, hour=21, tzinfo=UTC_TZ),
        ),
        # Change clock backward day, from BST to GMT
        (
            5,
            datetime.date(2017, 10, 29),
            datetime.datetime(2017, 10, 29, hour=0, tzinfo=UTC_TZ),
        ),
        (
            7,
            datetime.date(2017, 10, 29),
            datetime.datetime(2017, 10, 29, hour=1, tzinfo=UTC_TZ),
        ),
        (
            9,
            datetime.date(2017, 10, 29),
            datetime.datetime(2017, 10, 29, hour=2, tzinfo=UTC_TZ),
        ),
        (
            49,
            datetime.date(2017, 10, 29),
            datetime.datetime(2017, 10, 29, hour=22, tzinfo=UTC_TZ),
        ),
    ],
)
def test_convert_sp_and_date_to_utc_for_wholesale(sp, date, expected):
    """
    Test the convert_sp_and_date_to_utc function within a wholesale context
    for days where british time is the same as GMT, where british time is BST, and change days
    """
    assert (
        settlement_periods.convert_sp_and_date_to_utc(sp, date, is_wholesale=True)
        == expected
    )


@pytest.mark.parametrize(
    "utc,sp,date",
    [
        # British time is GMT
        (
            datetime.datetime(2016, 12, 31, hour=23, minute=30, tzinfo=UTC_TZ),
            2,
            datetime.date(2017, 1, 1),
        ),
        (
            datetime.datetime(2017, 1, 1, hour=22, tzinfo=UTC_TZ),
            47,
            datetime.date(2017, 1, 1),
        ),
        # British time is GMT
        (
            datetime.datetime(2017, 6, 30, hour=22, minute=30, tzinfo=UTC_TZ),
            2,
            datetime.date(2017, 7, 1),
        ),
        (
            datetime.datetime(2017, 7, 1, hour=21, tzinfo=UTC_TZ),
            47,
            datetime.date(2017, 7, 1),
        ),
        # Change clock forward day, from GMT to BST
        (
            datetime.datetime(2017, 3, 26, hour=0, minute=30, tzinfo=UTC_TZ),
            4,
            datetime.date(2017, 3, 26),
        ),
        (
            datetime.datetime(2017, 3, 26, hour=1, minute=30, tzinfo=UTC_TZ),
            6,
            datetime.date(2017, 3, 26),
        ),
        (
            datetime.datetime(2017, 3, 26, hour=2, minute=30, tzinfo=UTC_TZ),
            8,
            datetime.date(2017, 3, 26),
        ),
        (
            datetime.datetime(2017, 3, 26, hour=21, minute=30, tzinfo=UTC_TZ),
            46,
            datetime.date(2017, 3, 26),
        ),
        # Change clock backward day, from BST to GMT
        (
            datetime.datetime(2017, 10, 29, hour=0, minute=30, tzinfo=UTC_TZ),
            6,
            datetime.date(2017, 10, 29),
        ),
        (
            datetime.datetime(2017, 10, 29, hour=1, minute=30, tzinfo=UTC_TZ),
            8,
            datetime.date(2017, 10, 29),
        ),
        (
            datetime.datetime(2017, 10, 29, hour=2, minute=30, tzinfo=UTC_TZ),
            10,
            datetime.date(2017, 10, 29),
        ),
        (
            datetime.datetime(2017, 10, 29, hour=22, minute=30, tzinfo=UTC_TZ),
            50,
            datetime.date(2017, 10, 29),
        ),
    ],
)
def test_convert_utc_to_sp_and_date_for_wholesale(utc, sp, date):
    """
    Test the convert_utc_to_sp_and_date function within a wholesale context
    for days where british time is the same as GMT, where british time is BST, and change days
    """
    assert settlement_periods.convert_utc_to_sp_and_date(utc, is_wholesale=True) == (
        sp,
        date,
    )


@pytest.mark.parametrize(
    "sp,date,expected",
    [
        # British time is GMT
        (
            1,
            datetime.date(2016, 1, 1),
            datetime.datetime(2016, 1, 1, hour=0, tzinfo=UTC_TZ),
        ),
        (
            4,
            datetime.date(2016, 1, 1),
            datetime.datetime(2016, 1, 1, hour=1, minute=30, tzinfo=UTC_TZ),
        ),
        (
            20,
            datetime.date(2016, 1, 1),
            datetime.datetime(2016, 1, 1, hour=9, minute=30, tzinfo=UTC_TZ),
        ),
        # British time is BST
        (
            1,
            datetime.date(2016, 7, 1),
            datetime.datetime(2016, 6, 30, hour=23, tzinfo=UTC_TZ),
        ),
        (
            4,
            datetime.date(2016, 7, 1),
            datetime.datetime(2016, 7, 1, hour=0, minute=30, tzinfo=UTC_TZ),
        ),
        (
            20,
            datetime.date(2016, 7, 1),
            datetime.datetime(2016, 7, 1, hour=8, minute=30, tzinfo=UTC_TZ),
        ),
        # Change clock forward day, from GMT to BST
        (
            1,
            datetime.date(2016, 3, 27),
            datetime.datetime(2016, 3, 27, hour=0, tzinfo=UTC_TZ),
        ),
        (
            4,
            datetime.date(2016, 3, 27),
            datetime.datetime(2016, 3, 27, hour=1, minute=30, tzinfo=UTC_TZ),
        ),
        (
            20,
            datetime.date(2016, 3, 27),
            datetime.datetime(2016, 3, 27, hour=9, minute=30, tzinfo=UTC_TZ),
        ),
        # Change clock backward day, from BST to GMT
        (
            1,
            datetime.date(2015, 10, 25),
            datetime.datetime(2015, 10, 24, hour=23, tzinfo=UTC_TZ),
        ),
        (
            4,
            datetime.date(2015, 10, 25),
            datetime.datetime(2015, 10, 25, hour=0, minute=30, tzinfo=UTC_TZ),
        ),
        (
            20,
            datetime.date(2015, 10, 25),
            datetime.datetime(2015, 10, 25, hour=8, minute=30, tzinfo=UTC_TZ),
        ),
    ],
)
def test_convert_sp_and_date_to_utc_for_retail(sp, date, expected):
    """
    Test the convert_sp_and_date_to_utc function within a retail context
    for days where british time is the same as GMT, where british time is BST, and change days
    """
    assert settlement_periods.convert_sp_and_date_to_utc(sp, date) == expected


@pytest.mark.parametrize(
    "utc,sp,date",
    [
        # British time is GMT
        (
            datetime.datetime(2016, 1, 1, hour=0, tzinfo=UTC_TZ),
            1,
            datetime.date(2016, 1, 1),
        ),
        (
            datetime.datetime(2016, 1, 1, hour=1, minute=30, tzinfo=UTC_TZ),
            4,
            datetime.date(2016, 1, 1),
        ),
        (
            datetime.datetime(2016, 1, 1, hour=9, minute=30, tzinfo=UTC_TZ),
            20,
            datetime.date(2016, 1, 1),
        ),
        # British time is BST
        (
            datetime.datetime(2016, 6, 30, hour=23, tzinfo=UTC_TZ),
            1,
            datetime.date(2016, 7, 1),
        ),
        (
            datetime.datetime(2016, 7, 1, hour=0, minute=30, tzinfo=UTC_TZ),
            4,
            datetime.date(2016, 7, 1),
        ),
        (
            datetime.datetime(2016, 7, 1, hour=8, minute=30, tzinfo=UTC_TZ),
            20,
            datetime.date(2016, 7, 1),
        ),
        # Change clock forward day, From GMT to BST
        (
            datetime.datetime(2016, 3, 27, hour=0, tzinfo=UTC_TZ),
            1,
            datetime.date(2016, 3, 27),
        ),
        (
            datetime.datetime(2016, 3, 27, hour=1, minute=30, tzinfo=UTC_TZ),
            4,
            datetime.date(2016, 3, 27),
        ),
        (
            datetime.datetime(2016, 3, 27, hour=9, minute=30, tzinfo=UTC_TZ),
            20,
            datetime.date(2016, 3, 27),
        ),
        # Change clock backward day, from BST to GMT
        (
            datetime.datetime(2016, 10, 24, hour=23, tzinfo=UTC_TZ),
            1,
            datetime.date(2016, 10, 25),
        ),
        (
            datetime.datetime(2016, 10, 25, hour=0, minute=30, tzinfo=UTC_TZ),
            4,
            datetime.date(2016, 10, 25),
        ),
        (
            datetime.datetime(2016, 10, 25, hour=8, minute=30, tzinfo=UTC_TZ),
            20,
            datetime.date(2016, 10, 25),
        ),
    ],
)
def test_convert_utc_to_sp_and_date_for_retail(utc, sp, date):
    """
    Test the convert_utc_to_sp_and_date function within a retail context
    for days where british time is the same as GMT, where british time is BST, and change days
    """
    assert settlement_periods.convert_utc_to_sp_and_date(utc) == (sp, date)


@pytest.mark.parametrize(
    "start,end,periods",
    [
        (datetime.datetime(2016, 1, 1, 0, 0), datetime.datetime(2016, 1, 1, 0, 30), 1),
        (datetime.datetime(2016, 1, 1, 0, 0), datetime.datetime(2016, 1, 1, 4, 0), 8),
        (datetime.datetime(2016, 1, 1, 0, 0), datetime.datetime(2016, 1, 2, 0, 30), 49),
        # Clocks go forward here: only 23 hours in the day
        (
            datetime.datetime(2018, 3, 25, 0, 0),
            datetime.datetime(2018, 3, 26, 0, 0),
            46,
        ),
        # Clocks go backwards here: 25 hours in the day
        (
            datetime.datetime(2018, 10, 28, 0, 0),
            datetime.datetime(2018, 10, 29, 0, 0),
            50,
        ),
    ],
)
def test_number_of_settlement_periods_in_timedelta(start, end, periods):
    start = GB_TZ.normalize(GB_TZ.localize(start))
    end = GB_TZ.normalize(GB_TZ.localize(end))
    delta = end - start

    assert settlement_periods.number_of_periods_in_timedelta(delta) == periods


@pytest.mark.parametrize(
    "time,is_dst,expected",
    [
        (
            datetime.datetime(2016, 1, 1, 0, 0),
            None,
            datetime.datetime(2016, 1, 1, 0, 0),
        ),
        (
            datetime.datetime(2016, 1, 1, 0, 30),
            None,
            datetime.datetime(2016, 1, 1, 0, 30),
        ),
        (
            datetime.datetime(2016, 1, 1, 0, 15),
            None,
            datetime.datetime(2016, 1, 1, 0, 0),
        ),
        (
            datetime.datetime(2016, 1, 1, 0, 45),
            None,
            datetime.datetime(2016, 1, 1, 0, 30),
        ),
        # Hour before clocks change forward
        (
            datetime.datetime(2016, 3, 27, 0, 0),
            None,
            datetime.datetime(2016, 3, 27, 0, 0),
        ),
        # Hour after clocks change forward
        (
            datetime.datetime(2016, 3, 27, 2, 0),
            None,
            datetime.datetime(2016, 3, 27, 2, 0),
        ),
        # Hour before clocks change back
        (
            datetime.datetime(2016, 10, 30, 1, 0),
            True,
            datetime.datetime(2016, 10, 30, 1, 0),
        ),
        # Hour after clocks change back
        (
            datetime.datetime(2016, 10, 30, 1, 0),
            False,
            datetime.datetime(2016, 10, 30, 1, 0),
        ),
    ],
)
def test_round_down_local_time(time, is_dst, expected):
    # Operations within the hour stay in the same timezone & DST
    local_time = GB_TZ.localize(time, is_dst=is_dst)

    expected = GB_TZ.localize(expected, is_dst=is_dst)

    assert settlement_periods._round_local_down_to_hh(local_time) == expected

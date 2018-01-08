import datetime

import pytest
import pytz

from xocto import settlement_periods
from xocto.settlement_periods import convert_sp_and_date_to_utc, convert_utc_to_sp_and_date


@pytest.mark.parametrize("sp,date,expected", [
    # British time is GMT
    (1, datetime.date(2016, 1, 1), pytz.utc.localize(datetime.datetime(2016, 1, 1, hour=0))),
    (4, datetime.date(2016, 1, 1), pytz.utc.localize(datetime.datetime(2016, 1, 1, hour=1,
                                                                       minute=30))),
    (20, datetime.date(2016, 1, 1), pytz.utc.localize(datetime.datetime(2016, 1, 1, hour=9,
                                                                        minute=30))),

    # British time is BST
    (1, datetime.date(2016, 7, 1), pytz.utc.localize(datetime.datetime(2016, 6, 30, hour=23))),
    (4, datetime.date(2016, 7, 1), pytz.utc.localize(datetime.datetime(2016, 7, 1, hour=0,
                                                                       minute=30))),
    (20, datetime.date(2016, 7, 1), pytz.utc.localize(datetime.datetime(2016, 7, 1, hour=8,
                                                                        minute=30))),

    # Change clock forward day,
    # from GMT to BST
    (1, datetime.date(2016, 3, 27), pytz.utc.localize(datetime.datetime(2016, 3, 27, hour=0))),
    (4, datetime.date(2016, 3, 27), pytz.utc.localize(datetime.datetime(2016, 3, 27, hour=1,
                                                                        minute=30))),
    (20, datetime.date(2016, 3, 27), pytz.utc.localize(datetime.datetime(2016, 3, 27, hour=9,
                                                                         minute=30))),

    # Change clock backward day,
    # from BST to GMT
    (1, datetime.date(2015, 10, 25), pytz.utc.localize(datetime.datetime(2015, 10, 24, hour=23))),
    (4, datetime.date(2015, 10, 25), pytz.utc.localize(datetime.datetime(2015, 10, 25, hour=0,
                                                                         minute=30))),
    (20, datetime.date(2015, 10, 25), pytz.utc.localize(datetime.datetime(2015, 10, 25, hour=8,
                                                                          minute=30))),
])
def test_convert_sp_and_date_to_utc(sp, date, expected):
    """
    Test the convert_sp_and_date_to_utc function
    for days where british time is the same as GMT,
    where british time is BST,
    and change days
    """
    assert convert_sp_and_date_to_utc(sp, date) == expected


@pytest.mark.parametrize("utc,sp,date", [
    # British time is GMT
    (datetime.datetime(2016, 1, 1, hour=0, tzinfo=pytz.utc),
     1, datetime.datetime(2016, 1, 1).date()),
    (datetime.datetime(2016, 1, 1, hour=1, minute=30, tzinfo=pytz.utc),
     4, datetime.datetime(2016, 1, 1).date()),
    (datetime.datetime(2016, 1, 1, hour=9, minute=30, tzinfo=pytz.utc),
     20, datetime.datetime(2016, 1, 1).date()),

    # British time is BST
    (datetime.datetime(2016, 6, 30, hour=23, tzinfo=pytz.utc),
     1, datetime.datetime(2016, 7, 1).date()),
    (datetime.datetime(2016, 7, 1, hour=0, minute=30, tzinfo=pytz.utc),
     4, datetime.datetime(2016, 7, 1).date()),
    (datetime.datetime(2016, 7, 1, hour=8, minute=30, tzinfo=pytz.utc),
     20, datetime.datetime(2016, 7, 1).date()),

    # Change clock forward day,
    # From GMT to BST
    (datetime.datetime(2016, 3, 27, hour=0, tzinfo=pytz.utc),
     1, datetime.datetime(2016, 3, 27).date()),
    (datetime.datetime(2016, 3, 27, hour=1, minute=30, tzinfo=pytz.utc),
     4, datetime.datetime(2016, 3, 27).date()),
    (datetime.datetime(2016, 3, 27, hour=9, minute=30, tzinfo=pytz.utc),
     20, datetime.datetime(2016, 3, 27).date()),

    # Change clock backward day,
    # from BST to GMT
    (datetime.datetime(2016, 10, 24, hour=23, tzinfo=pytz.utc),
     1, datetime.datetime(2016, 10, 25).date()),
    (datetime.datetime(2016, 10, 25, hour=0, minute=30, tzinfo=pytz.utc),
     4, datetime.datetime(2016, 10, 25).date()),
    (datetime.datetime(2016, 10, 25, hour=8, minute=30, tzinfo=pytz.utc),
     20, datetime.datetime(2016, 10, 25).date()),
])
def test_convert_utc_to_sp_and_date(utc, sp, date):
    """
    Test the convert_utc_to_sp_and_date function
    for days where british time is the same as GMT,
    where british time is BST,
    and change days
    """

    assert convert_utc_to_sp_and_date(utc) == (sp, date)


@pytest.mark.parametrize(
    "start,end,periods",
    [
        (datetime.datetime(2016, 1, 1, 0, 0), datetime.datetime(2016, 1, 1, 0, 30), 1),
        (datetime.datetime(2016, 1, 1, 0, 0), datetime.datetime(2016, 1, 1, 4, 0), 8),
        (datetime.datetime(2016, 1, 1, 0, 0), datetime.datetime(2016, 1, 2, 0, 30), 49),
        # Clocks go forward here: only 23 hours in the day
        (datetime.datetime(2018, 3, 25, 0, 0), datetime.datetime(2018, 3, 26, 0, 0), 46),
        # Clocks go backwards here: 25 hours in the day
        (datetime.datetime(2018, 10, 28, 0, 0), datetime.datetime(2018, 10, 29, 0, 0), 50),
    ]
)
def test_number_of_settlement_periods_in_timedelta(start, end, periods):
    tz = pytz.timezone('Europe/London')
    start = tz.normalize(tz.localize(start))
    end = tz.normalize(tz.localize(end))
    delta = end - start
    assert settlement_periods.number_of_periods_in_timedelta(delta) == periods

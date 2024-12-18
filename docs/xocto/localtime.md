# Localtime

## Module for working with dates, times and timezones

Used over the years internally in Kraken Technologies, this module is a battle tested and well reviewed module for working with dates, times and timezones. The main API it presents is composed of a series of functions which accept a date/datetime object, and manipulate it in one form or another.

## Examples

```python
from xocto import localtime
>>> now = localtime.now()
>>> now
2022-04-20 14:57:53.045707+02:00
>>> localtime.seconds_in_the_future(n=10, dt=now)
2022-04-20 14:58:03.045707+02:00
>>> localtime.nearest_half_hour(now)
2022-04-20 15:00:00+02:00
```

See [xocto.localtime](https://github.com/octoenergy/xocto/blob/master/xocto/localtime.py) for more details, including examples and in depth technical details.

## Localising datetimes between different timezones

`localtime` can be used to change the timezone of a datetime e.g.

```python
london_tz = zoneinfo.ZoneInfo("Europe/London")
dt = datetime.datetime(2024, 1, 1, tzinfo=london_tz)

sydney_tz = zoneinfo.ZoneInfo("Australia/Sydney")
localtime.as_localtime(dt, tz=sydney_tz)
=> datetime.datetime(2024, 1, 1, 11, 0, tzinfo=zoneinfo.ZoneInfo(key='Australia/Sydney'))

localtime.as_utc(dt)
=> datetime.datetime(2024, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo(key='UTC'))
```

Behaviour around Daylight Savings Time (DST) boundaries - where
clocks go forward or back - can be surprising e.g.

```python
# Normally "2AM - 0AM" should be "2 hours". However, in
# GBR clocks go forward on this day at 1AM => 2AM. This
# means after "as_utc" we are actually doing "1AM - 0AM".
localtime.as_utc(datetime(2020, 3, 29, hour=2, tzinfo=london_tz)) -
localtime.as_utc(datetime(2020, 3, 29, hour=0, tzinfo=london_tz))
=> timedelta(seconds=3600)
```

You should consider the implications of DST when localizing to a
different timezone - especially when working with ranges.

### Non-existent datetimes

Python datetimes can be constructed for times that don't
actually exist in certain timezones, due to DST changes e.g.

```python
# Doesn't exist in GBR as at this time the clocks went
# forwards one hour - to 2AM.
datetime(2020, 3, 29, hours=1, tzinfo=london_tz)

# Python datetime operations do not consider DST when
# doing calculations on datetimes. Although "2AM - 1AM"
# is normally "1 hour", the example below is wrong as
# in GBR the clocks went forward here: 1AM => 2AM - so
# the time that actually elapsed was "0".
datetime(2020, 3, 29, hour=2, tzinfo=london_tz) -
datetime(2020, 3, 29, hour=1, tzinfo=london_tz)
=> datetime.timedelta(seconds=3600)  # <== WRONG (should be 0)
```

To ensure a datetime exists in its timezone, convert it to UTC
(a timezone without DST) and back again e.g.

```python
localtime.as_localtime(localtime.as_utc(my_dt), tz=target_tz)
```

Although such datetimes are unlikely to be created directly, they
may be created from other code in `datetime` e.g.

```python
datetime(2020, 3, 29, tzinfo=london_tz) + timedelta(hours=1)
=> datetime(2020, 3, 29, hours=1, tzinfo=london_tz)
```


## Variables

```{eval-rst}
.. autodata:: xocto.localtime.far_future
.. autodata:: xocto.localtime.far_past
.. autodata:: xocto.localtime.UTC
.. autodata:: xocto.localtime.LONDON
.. autodata:: xocto.localtime.ONE_DAY
.. autodata:: xocto.localtime.ONE_HOUR
.. autodata:: xocto.localtime.MIDNIGHT_TIME
```

## API Reference

```{eval-rst}

.. module:: xocto.types

.. automodule:: xocto.localtime
   :members:
   :undoc-members:
   :show-inheritance:
```

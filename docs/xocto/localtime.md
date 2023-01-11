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

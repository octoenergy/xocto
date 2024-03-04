# Model Fields

Custom [Django model fields](https://docs.djangoproject.com/en/dev/ref/models/fields/).


## Postgres specific fields

Fields that can only be used with a Postgres database, enhancing the functionality
provided by [django.contrib.postgres.fields](https://docs.djangoproject.com/en/dev/ref/contrib/postgres/fields/).

### Ranges

Provides [range fields](https://docs.djangoproject.com/en/dev/ref/contrib/postgres/fields/#range-fields) that work
with the `Range` classes from [xocto.ranges](./ranges.md).

The underlying Range type exposed by the Django ORM is `psycopg2.extras.Range` which is awkward to
use throughout an application, and requires lots of boilerplate code to work with correctly.

Alternatively, `xocto.ranges` are designed to be used throughout an application. These fields
make it possible to interact with them directly from the Django ORM.

Migrating from the Django range types to these range types is straightforward and does
not require any changes to the database schema. The migration file generated will refer
to the new fields, but since the underlying database type is the same, the migration will
be a no-op.

The standard Django query operators are almost the same as for the built-in types.
They accept `xocto.ranges` as arguments, but don't support passing in a tuple of values:

```python

assert SalesPeriod.objects.filter(
    period__contains=ranges.FiniteDateRange(
        start=datetime.date(2020, 1, 10),
        end=datetime.date(2020, 1, 20),
    )
).exists()

assert SalesPeriod.objects.filter(
    period__overlaps=ranges.FiniteDateRange(
        start=datetime.date(2020, 1, 10),
        end=datetime.date(2020, 1, 20),
    )
).exists()

# ERROR! This will raise a TypeError
SalesPeriod.objects.filter(period__overlaps=(datetime.date(2020, 1, 10), datetime.date(2020, 1, 20)))

```

#### FiniteDateRangeField

Module: `xocto.fields.postgres.ranges.FiniteDateRangeField`\
Bounds: `[]`\
Type: [xocto.ranges.FiniteDateRange](xocto.ranges.FiniteDateRange)

A field that represents an inclusive-inclusive `[]` ranges of dates. The start
and end of the range are inclusive and must not be `None`.

```python
import datetime
from django.db import models
from xocto import ranges
from xocto.fields.postgres import ranges as db_ranges

class SalesPeriod(models.Model):
    ...
    period = db_ranges.FiniteDateRangeField()

sales_period = SalesPeriod.objects.create(
    period=ranges.FiniteDateRange(
        start=datetime.date(2020, 1, 1),
        end=datetime.date(2020, 1, 31)
    ),
    ...
)

assert sales_period.period == ranges.FiniteDateRange(
    start=datetime.date(2020, 1, 1),
    end=datetime.date(2020, 1, 31)
)
assert sales_period.period.start == datetime.date(2020, 1, 1)
```


#### FiniteDateTimeRangeField

Module: `xocto.fields.postgres.ranges.FiniteDateTimeRangeField`\
Bounds: `[)`\
Type: [xocto.ranges.FiniteDatetimeRange](xocto.ranges.FiniteDatetimeRange)

A field that represents an inclusive-exclusive `[)` ranges of timezone-aware
datetimes. Both the start and end of the range must not be `None`.

The values returned from the database will always be converted to the local timezone
as per the `TIME_ZONE` setting in `settings.py`.

```python
import datetime
from django.db import models
from xocto import ranges, localtime
from xocto.fields.postgres import ranges as db_ranges

class CalendarEntry(models.Model):
    ...
    event_time = db_ranges.FiniteDateTimeRangeField()

calendar_entry = CalendarEntry.objects.create(
    event_time=ranges.FiniteDatetimeRange(
        start=localtime.datetime(2020, 1, 1, 14, 30),
        end=localtime.datetime(2020, 1, 1, 15, 30)
    ),
    ...
)

assert calendar_entry.event_time == ranges.FiniteDatetimeRange(
    start=localtime.datetime(2020, 1, 1, 14, 30),
    end=localtime.datetime(2020, 1, 1, 15, 30)
)
assert calendar_entry.event_time.start == localtime.datetime(2020, 1, 1, 14, 30)
```


#### HalfFiniteDateTimeRangeField

Module: `xocto.fields.postgres.ranges.HalfFiniteDateTimeRangeField`\
Bounds: `[)`\
Type: [xocto.ranges.HalfFiniteDatetimeRange](xocto.ranges.HalfFiniteRange)

> **_NOTE:_** docs can not link directly to `HalfFiniteDatetimeRange` at this stage as it's a type alias

A field that represents an inclusive-exclusive `[)` ranges of timezone-aware
datetimes. The end of the range may be open-ended, represented by `None`.

The values returned from the database will always be converted to the local timezone
as per the `TIME_ZONE` setting in `settings.py`.

```python
import datetime
from django.db import models
from xocto import ranges, localtime
from xocto.fields.postgres import ranges as db_ranges

class Agreement(models.Model):
    ...
    period = db_ranges.HalfFiniteDateTimeRangeField()

agreement = Agreement.objects.create(
    period=ranges.HalfFiniteDatetimeRange(
        start=localtime.datetime(2020, 1, 1, 14, 30),
        end=None,
    ),
    ...
)

assert agreement.period == ranges.HalfFiniteDatetimeRange(
    start=localtime.datetime(2020, 1, 1, 14, 30),
    end=None
)
assert agreement.period.start == localtime.datetime(2020, 1, 1, 14, 30)
```

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

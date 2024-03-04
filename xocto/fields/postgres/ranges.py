"""
Adapter fields for postgres range types that return xocto.Range python objects.
"""

import datetime
import json
from typing import Optional

from django.contrib.postgres import fields as pg_fields
from django.contrib.postgres.fields import ranges as pg_ranges
from django.contrib.postgres.fields import utils as pg_utils
from django.db import models

from xocto import localtime, ranges


class FiniteDateRangeField(pg_fields.DateRangeField):
    """
    A DateRangeField with Inclusive-Inclusive [] bounds.

    The underlying postgres type will always store the range as Inclusive-Exclusive [).
    This field will always translate to [].

    Accepts and returns xocto.ranges.FiniteDateRange objects.
    """

    def get_prep_value(
        self, value: Optional[ranges.FiniteDateRange]
    ) -> Optional[pg_ranges.DateRange]:
        if value is None:
            return None
        if not isinstance(value, ranges.FiniteDateRange):
            raise TypeError(
                "FiniteDateRangeField may only accept FiniteDateRange objects."
            )
        return pg_ranges.DateRange(lower=value.start, upper=value.end, bounds="[]")

    def from_db_value(
        self,
        value: Optional[pg_ranges.DateRange],
        expression: object,
        connection: object,
    ) -> Optional[ranges.FiniteDateRange]:
        if value is None:
            return None
        return ranges.FiniteDateRange(
            start=value.lower, end=self._upper_to_inclusive(value)
        )

    def to_python(self, value: Optional[str]) -> Optional[ranges.FiniteDateRange]:
        if value is None:
            return None
        obj = json.loads(value)
        return ranges.FiniteDateRange(
            start=self.base_field.to_python(obj["start"]),
            end=self.base_field.to_python(obj["end"]),
        )

    def value_to_string(self, obj: models.Model) -> Optional[str]:
        value: Optional[ranges.FiniteDateRange] = self.value_from_object(obj)
        if value is None:
            return None
        if not isinstance(value, ranges.FiniteDateRange):
            raise TypeError(
                "FiniteDateRangeField may only accept FiniteDateRange objects."
            )
        base_field = self.base_field
        start = pg_utils.AttributeSetter(base_field.attname, value.start)
        end = pg_utils.AttributeSetter(base_field.attname, value.end)
        return json.dumps(
            {
                "start": base_field.value_to_string(start),
                "end": base_field.value_to_string(end),
            }
        )

    def _upper_to_inclusive(self, value: pg_ranges.DateRange) -> datetime.date:
        """
        Transform an exclusive upper bound to an inclusive bound.

        DateRanges (as all discrete ranges) are always stored as [) in the database, even if the
        input was []. [X, Y] is equivalent to [X, Y+1) in the database. When we read the value
        from the database, we need to subtract 1 day from the upper bound to return it to inclusive.
        """
        if value.upper_inc:
            return value.upper
        return value.upper - datetime.timedelta(days=1)


class FiniteDateTimeRangeField(pg_fields.DateTimeRangeField):
    """
    A DateTimeRangeField with Inclusive-Exclusive [) bounds that aren't infinite.

    Accepts and returns xocto.ranges.FiniteDatetimeRange objects. Values are always
    timezone-aware, and will be converted to the timezone specified in django settings.
    """

    def get_prep_value(
        self, value: Optional[ranges.FiniteDatetimeRange]
    ) -> Optional[pg_ranges.DateTimeTZRange]:
        if value is None:
            return None
        if not isinstance(value, ranges.FiniteDatetimeRange):
            raise TypeError(
                "FiniteDateTimeRangeField may only accept FiniteDatetimeRange objects."
            )
        return pg_ranges.DateTimeTZRange(
            lower=value.start, upper=value.end, bounds="[)"
        )

    def from_db_value(
        self,
        value: Optional[pg_ranges.DateTimeTZRange],
        expression: object,
        connection: object,
    ) -> Optional[ranges.FiniteDatetimeRange]:
        if value is None:
            return None
        return ranges.FiniteDatetimeRange(
            start=localtime.as_localtime(value.lower),
            end=localtime.as_localtime(value.upper),
        )

    def to_python(self, value: Optional[str]) -> Optional[ranges.FiniteDatetimeRange]:
        if value is None:
            return None
        obj = json.loads(value)
        return ranges.FiniteDatetimeRange(
            start=localtime.as_localtime(self.base_field.to_python(obj["start"])),
            end=localtime.as_localtime(self.base_field.to_python(obj["end"])),
        )

    def value_to_string(self, obj: models.Model) -> Optional[str]:
        value: Optional[ranges.FiniteDatetimeRange] = self.value_from_object(obj)
        if value is None:
            return None
        if not isinstance(value, ranges.FiniteDatetimeRange):
            raise TypeError(
                "FiniteDateTimeRangeField may only accept FiniteDatetimeRange objects."
            )
        base_field = self.base_field
        start = pg_utils.AttributeSetter(base_field.attname, value.start)
        end = pg_utils.AttributeSetter(base_field.attname, value.end)
        return json.dumps(
            {
                "start": base_field.value_to_string(start),
                "end": base_field.value_to_string(end),
            }
        )


class HalfFiniteDateTimeRangeField(pg_fields.DateTimeRangeField):
    """
    A DateTimeRangeField with Inclusive-Exclusive [) bounds that allows an infinite/open upper bound.

    Accepts and returns xocto.ranges.HalfFiniteDatetimeRange objects. Values are always
    timezone-aware, and will be converted to the timezone specified in django settings.
    """

    def get_prep_value(
        self, value: Optional[ranges.HalfFiniteDatetimeRange]
    ) -> Optional[pg_ranges.DateTimeTZRange]:
        if value is None:
            return None
        if (
            # HalfFiniteDatetimeRange is a subscripted generic and may not be checked with
            # isinstance directly. So, we check for it's parent class and attribute values.
            not isinstance(value, ranges.HalfFiniteRange)  # type: ignore [redundant-expr]
            or not isinstance(value.start, datetime.datetime)  # type: ignore [redundant-expr]
            or (value.end is not None and not isinstance(value.end, datetime.datetime))
        ):
            raise TypeError(
                "HalfFiniteDateTimeRangeField may only accept HalfFiniteDatetimeRange objects."
            )
        return pg_ranges.DateTimeTZRange(
            lower=value.start, upper=value.end, bounds="[)"
        )

    def from_db_value(
        self,
        value: Optional[pg_ranges.DateTimeTZRange],
        expression: object,
        connection: object,
    ) -> Optional[ranges.HalfFiniteDatetimeRange]:
        if value is None:
            return None
        return ranges.HalfFiniteDatetimeRange(
            start=localtime.as_localtime(value.lower),
            end=localtime.as_localtime(value.upper) if value.upper else None,
        )

    def to_python(
        self, value: Optional[str]
    ) -> Optional[ranges.HalfFiniteDatetimeRange]:
        if value is None:
            return None
        obj = json.loads(value)
        end = self.base_field.to_python(obj["end"])
        return ranges.HalfFiniteDatetimeRange(
            start=localtime.as_localtime(self.base_field.to_python(obj["start"])),
            end=localtime.as_localtime(end) if end else None,
        )

    def value_to_string(self, obj: models.Model) -> Optional[str]:
        value: Optional[ranges.HalfFiniteDatetimeRange] = self.value_from_object(obj)
        if value is None:
            return None
        if not isinstance(value, ranges.HalfFiniteRange):
            raise TypeError(
                "HalfFiniteDateTimeRangeField may only accept HalfFiniteDatetimeRange objects."
            )
        base_field = self.base_field
        start = pg_utils.AttributeSetter(base_field.attname, value.start)
        end = pg_utils.AttributeSetter(base_field.attname, value.end)
        return json.dumps(
            {
                "start": base_field.value_to_string(start),
                "end": base_field.value_to_string(end),
            }
        )

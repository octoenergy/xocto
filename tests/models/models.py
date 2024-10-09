from django.db import models

from xocto.fields.postgres import ranges as range_fields


class FiniteDateRangeModel(models.Model):
    finite_date_range = range_fields.FiniteDateRangeField()
    finite_date_range_nullable = range_fields.FiniteDateRangeField(null=True)


class FiniteDateTimeRangeModel(models.Model):
    finite_datetime_range = range_fields.FiniteDateTimeRangeField()
    finite_datetime_range_nullable = range_fields.FiniteDateTimeRangeField(null=True)
    finite_datetime_range_utc = range_fields.FiniteDateTimeRangeField(
        as_localtime=False, null=True
    )


class HalfFiniteDateTimeRangeModel(models.Model):
    half_finite_datetime_range = range_fields.HalfFiniteDateTimeRangeField()
    half_finite_datetime_range_nullable = range_fields.HalfFiniteDateTimeRangeField(
        null=True
    )
    half_finite_datetime_range_utc = range_fields.HalfFiniteDateTimeRangeField(
        as_localtime=False, null=True
    )

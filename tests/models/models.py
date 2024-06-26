from django.db import models

from xocto.fields.postgres import ltree
from xocto.fields.postgres import ranges as range_fields


class FiniteDateRangeModel(models.Model):
    finite_date_range = range_fields.FiniteDateRangeField()
    finite_date_range_nullable = range_fields.FiniteDateRangeField(null=True)


class FiniteDateTimeRangeModel(models.Model):
    finite_datetime_range = range_fields.FiniteDateTimeRangeField()
    finite_datetime_range_nullable = range_fields.FiniteDateTimeRangeField(null=True)


class HalfFiniteDateTimeRangeModel(models.Model):
    half_finite_datetime_range = range_fields.HalfFiniteDateTimeRangeField()
    half_finite_datetime_range_nullable = range_fields.HalfFiniteDateTimeRangeField(
        null=True
    )


class TreeModel(models.Model):
    parent = models.ForeignKey("self", null=True, on_delete=models.SET_NULL)
    path = ltree.LtreeField()

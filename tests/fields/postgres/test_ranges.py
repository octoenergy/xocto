import datetime
import zoneinfo

import pytest
from django.core import serializers
from django.utils import timezone

from tests.models import models
from xocto import localtime, ranges


pytestmark = pytest.mark.django_db

TZ_MELB = zoneinfo.ZoneInfo("Australia/Melbourne")


class TestFiniteDateRangeField:
    def test_roundtrip(self):
        finite_date_range = ranges.FiniteDateRange(
            start=datetime.date(2024, 1, 10), end=datetime.date(2024, 2, 9)
        )
        obj = models.FiniteDateRangeModel.objects.create(
            finite_date_range=finite_date_range
        )
        queried = models.FiniteDateRangeModel.objects.get(pk=obj.pk)
        assert queried.finite_date_range == finite_date_range

    def test_nullable(self):
        obj = models.FiniteDateRangeModel.objects.create(
            finite_date_range=ranges.FiniteDateRange(
                start=datetime.date(2024, 1, 10), end=datetime.date(2024, 2, 9)
            ),
            finite_date_range_nullable=None,
        )
        queried = models.FiniteDateRangeModel.objects.get(pk=obj.pk)
        assert queried.finite_date_range_nullable is None

    def test_query(self):
        finite_date_range = ranges.FiniteDateRange(
            start=datetime.date(2024, 1, 10), end=datetime.date(2024, 2, 9)
        )
        models.FiniteDateRangeModel.objects.create(finite_date_range=finite_date_range)
        assert models.FiniteDateRangeModel.objects.filter(
            finite_date_range=finite_date_range
        ).exists()
        assert models.FiniteDateRangeModel.objects.filter(
            finite_date_range__overlap=ranges.FiniteDateRange(
                start=datetime.date(2024, 1, 1), end=datetime.date(2024, 1, 15)
            )
        ).exists()
        assert models.FiniteDateRangeModel.objects.filter(
            finite_date_range__contains=ranges.FiniteDateRange(
                start=datetime.date(2024, 1, 11), end=datetime.date(2024, 1, 15)
            )
        ).exists()
        assert not models.FiniteDateRangeModel.objects.filter(
            finite_date_range__contains=ranges.FiniteDateRange(
                start=datetime.date(2024, 1, 5), end=datetime.date(2024, 1, 15)
            )
        ).exists()

    def test_serialization(self):
        obj = models.FiniteDateRangeModel.objects.create(
            finite_date_range=ranges.FiniteDateRange(
                start=datetime.date(2024, 1, 10), end=datetime.date(2024, 2, 9)
            )
        )
        dumped = serializers.serialize("json", [obj])
        loaded = list(serializers.deserialize("json", dumped))
        loaded_obj = loaded[0].object
        assert obj == loaded_obj
        assert obj.finite_date_range == loaded_obj.finite_date_range
        assert obj.finite_date_range_nullable == loaded_obj.finite_date_range_nullable


class TestFiniteDateTimeRangeField:
    def test_roundtrip(self):
        finite_datetime_range = ranges.FiniteDatetimeRange(
            start=localtime.datetime(2024, 1, 10), end=localtime.datetime(2024, 2, 9)
        )
        obj = models.FiniteDateTimeRangeModel.objects.create(
            finite_datetime_range=finite_datetime_range
        )
        queried = models.FiniteDateTimeRangeModel.objects.get(pk=obj.pk)
        assert queried.finite_datetime_range == finite_datetime_range

    def test_nullable(self):
        obj = models.FiniteDateTimeRangeModel.objects.create(
            finite_datetime_range=ranges.FiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 10),
                end=localtime.datetime(2024, 2, 9),
            ),
            finite_datetime_range_nullable=None,
        )
        queried = models.FiniteDateTimeRangeModel.objects.get(pk=obj.pk)
        assert queried.finite_datetime_range_nullable is None

    def test_query(self):
        finite_datetime_range = ranges.FiniteDatetimeRange(
            start=localtime.datetime(2024, 1, 10), end=localtime.datetime(2024, 2, 9)
        )
        models.FiniteDateTimeRangeModel.objects.create(
            finite_datetime_range=finite_datetime_range
        )
        assert models.FiniteDateTimeRangeModel.objects.filter(
            finite_datetime_range=finite_datetime_range
        ).exists()
        assert models.FiniteDateTimeRangeModel.objects.filter(
            finite_datetime_range__overlap=ranges.FiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 1),
                end=localtime.datetime(2024, 1, 15),
            )
        ).exists()
        assert models.FiniteDateTimeRangeModel.objects.filter(
            finite_datetime_range__contains=ranges.FiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 11),
                end=localtime.datetime(2024, 1, 15),
            )
        ).exists()
        assert not models.FiniteDateTimeRangeModel.objects.filter(
            finite_datetime_range__contains=ranges.FiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 5),
                end=localtime.datetime(2024, 1, 15),
            )
        ).exists()

    def test_serialization(self):
        obj = models.FiniteDateTimeRangeModel.objects.create(
            finite_datetime_range=ranges.FiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 10),
                end=localtime.datetime(2024, 2, 9),
            )
        )
        dumped = serializers.serialize("json", [obj])
        loaded = list(serializers.deserialize("json", dumped))
        loaded_obj = loaded[0].object
        assert obj == loaded_obj
        assert obj.finite_datetime_range == loaded_obj.finite_datetime_range
        assert (
            obj.finite_datetime_range_nullable
            == loaded_obj.finite_datetime_range_nullable
        )

    def test_timezone_conversions(self):
        """
        Timezones are converted correctly when round tripping.
        """
        finite_datetime_range_melb = ranges.FiniteDatetimeRange(
            start=datetime.datetime(2024, 1, 10, tzinfo=TZ_MELB),
            end=datetime.datetime(2024, 2, 9, tzinfo=TZ_MELB),
        )
        obj = models.FiniteDateTimeRangeModel.objects.create(
            finite_datetime_range=finite_datetime_range_melb,
        )
        finite_datetime_range_london = ranges.FiniteDatetimeRange(
            start=timezone.localtime(finite_datetime_range_melb.start),
            end=timezone.localtime(finite_datetime_range_melb.end),
        )
        obj.refresh_from_db()
        assert (
            obj.finite_datetime_range
            == finite_datetime_range_london
            == finite_datetime_range_melb
        )
        assert obj.finite_datetime_range.start.tzinfo != TZ_MELB


class TestHalfFiniteDateTimeRangeField:
    def test_roundtrip(self):
        half_finite_datetime_range = ranges.HalfFiniteDatetimeRange(
            start=localtime.datetime(2024, 1, 10), end=None
        )
        obj = models.HalfFiniteDateTimeRangeModel.objects.create(
            half_finite_datetime_range=half_finite_datetime_range
        )
        queried = models.HalfFiniteDateTimeRangeModel.objects.get(pk=obj.pk)
        assert queried.half_finite_datetime_range == half_finite_datetime_range

    def test_nullable(self):
        obj = models.HalfFiniteDateTimeRangeModel.objects.create(
            half_finite_datetime_range=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 10),
                end=None,
            ),
            half_finite_datetime_range_nullable=None,
        )
        queried = models.HalfFiniteDateTimeRangeModel.objects.get(pk=obj.pk)
        assert queried.half_finite_datetime_range_nullable is None

    def test_query(self):
        half_finite_datetime_range = ranges.HalfFiniteDatetimeRange(
            start=localtime.datetime(2024, 1, 10), end=None
        )
        models.HalfFiniteDateTimeRangeModel.objects.create(
            half_finite_datetime_range=half_finite_datetime_range
        )
        assert models.HalfFiniteDateTimeRangeModel.objects.filter(
            half_finite_datetime_range=half_finite_datetime_range
        ).exists()
        assert models.HalfFiniteDateTimeRangeModel.objects.filter(
            half_finite_datetime_range__overlap=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 1),
                end=localtime.datetime(2024, 1, 15),
            )
        ).exists()
        assert models.HalfFiniteDateTimeRangeModel.objects.filter(
            half_finite_datetime_range__overlap=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 1),
                end=None,
            )
        ).exists()
        assert models.HalfFiniteDateTimeRangeModel.objects.filter(
            half_finite_datetime_range__contains=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 11),
                end=localtime.datetime(2024, 1, 15),
            )
        ).exists()
        assert models.HalfFiniteDateTimeRangeModel.objects.filter(
            half_finite_datetime_range__contains=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 11),
                end=None,
            )
        ).exists()
        assert not models.HalfFiniteDateTimeRangeModel.objects.filter(
            half_finite_datetime_range__contains=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 5),
                end=localtime.datetime(2024, 1, 15),
            )
        ).exists()
        assert not models.HalfFiniteDateTimeRangeModel.objects.filter(
            half_finite_datetime_range__contains=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 5),
                end=None,
            )
        ).exists()

    def test_serialization(self):
        obj = models.HalfFiniteDateTimeRangeModel.objects.create(
            half_finite_datetime_range=ranges.HalfFiniteDatetimeRange(
                start=localtime.datetime(2024, 1, 10),
                end=localtime.datetime(2024, 2, 9),
            )
        )
        dumped = serializers.serialize("json", [obj])
        loaded = list(serializers.deserialize("json", dumped))
        loaded_obj = loaded[0].object
        assert obj == loaded_obj
        assert obj.half_finite_datetime_range == loaded_obj.half_finite_datetime_range
        assert (
            obj.half_finite_datetime_range_nullable
            == loaded_obj.half_finite_datetime_range_nullable
        )

    def test_timezone_conversions(self):
        """
        Timezones are converted correctly when round tripping.
        """
        half_finite_datetime_range_melb = ranges.HalfFiniteDatetimeRange(
            start=datetime.datetime(2024, 1, 10, tzinfo=TZ_MELB),
            end=None,
        )
        obj = models.HalfFiniteDateTimeRangeModel.objects.create(
            half_finite_datetime_range=half_finite_datetime_range_melb,
        )
        half_finite_datetime_range_london = ranges.HalfFiniteDatetimeRange(
            start=timezone.localtime(half_finite_datetime_range_melb.start),
            end=None,
        )
        obj.refresh_from_db()
        assert (
            obj.half_finite_datetime_range
            == half_finite_datetime_range_london
            == half_finite_datetime_range_melb
        )
        assert obj.half_finite_datetime_range.start.tzinfo != TZ_MELB

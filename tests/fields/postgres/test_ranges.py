import datetime

import pytest
from django.core import serializers

from tests.models import models
from xocto import ranges


pytestmark = pytest.mark.django_db


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

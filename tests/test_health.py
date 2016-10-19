import pytest

from xocto import health


@pytest.mark.django_db
def test_defaults_to_zero():
    assert health._num_unapplied_migrations() == 0

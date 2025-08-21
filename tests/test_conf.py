from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import override_settings


def run_system_checks() -> str:
    stderr = StringIO()
    call_command("check", "-t", "xocto", deploy=True, stderr=stderr)
    return stderr.getvalue()


def test_valid_settings():
    output = run_system_checks()
    assert "xocto.E001" not in output
    assert "xocto.W001" not in output


@override_settings(BOTO_S3_TOTAL_MAX_ATTEMPTS="notanint")
def test_incorrect_setting_type():
    with pytest.raises(SystemCheckError) as exc_info:
        run_system_checks()
    assert (
        "(xocto.E001) settings.BOTO_S3_TOTAL_MAX_ATTEMPTS is the wrong type: expected NoneType/int, got str"
        in exc_info.value.args[0]
    )

from __future__ import annotations

from typing import Any

import pytest

from tests.storage.helpers import fixtures as fixture_helpers


# Fixture (as in files used in testing) loading


def _get_fixture_filepath(filepath: str) -> str:
    return str(fixture_helpers.fixture_filepath(filepath))


def _load_fixture(filepath: str, root: str | None = None, **kwargs: Any) -> Any:
    """
    Return the contents of a fixture file.

    If the file is a JSON file, we return the Python payload (not the JSON
    string).
    """
    if filepath.endswith(".json"):
        return fixture_helpers.load_json(filepath, root, **kwargs)
    else:
        return fixture_helpers.load_fixture(filepath, **kwargs)


@pytest.fixture()
def fixture():
    """
    Return a function that loads the contents of a test fixture.
    """
    return _load_fixture


@pytest.fixture()
def fixture_path():
    return _get_fixture_filepath

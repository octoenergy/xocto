from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union


def fixture_filepath(filepath: str) -> Path:
    return Path(__file__).parent.parent / "fixtures" / filepath


def load_fixture(filepath: str, **kwargs: Any) -> Union[str, bytes]:
    """
    Return the contents of a fixture file.

    Kwargs are passed to the ``open`` function.
    """
    with fixture_filepath(filepath).open(**kwargs) as f:
        return f.read()


def load_json(filepath: str, root: str | None = None, **kwargs: Any) -> Any:
    """
    Return the parsed contents of a JSON fixture file.

    Kwargs are passed to the ``open`` function.
    """
    with fixture_filepath(filepath).open(**kwargs) as f:
        data = json.load(f)
        if root is not None:
            return data[root]
        return data

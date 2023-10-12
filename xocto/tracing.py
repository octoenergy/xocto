from __future__ import annotations

import ddtrace


tracer = ddtrace.tracer
wrap = tracer.wrap


def set_tags(tags: dict[str | bytes, str]) -> None:
    """
    Set multiple tags on the current span.
    """
    span = tracer.current_span()
    if span:
        span.set_tags(tags)


def set_tag(key: str, value: object) -> None:
    """
    Set a tag on the current span.
    """
    span = tracer.current_span()
    if span:
        span.set_tag(key, value)


def set_global_tag(key: str, value: object) -> None:
    """
    Set a tag on the current root span.

    These tags will be associated to the entire Datadog trace.
    """
    span = tracer.current_root_span()
    if span:
        span.set_tag(key, value)

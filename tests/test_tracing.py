import ddtrace

from xocto import tracing

# set_tags


def test_set_tags_single_string_tag(mocker):
    span = ddtrace.Span(name="active-span")
    mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
    return_value = tracing.set_tags({"foo": "bar"})
    assert span.get_tag("foo") == "bar"
    assert return_value is None


def test_set_tags_single_bytes_tag(mocker):
    span = ddtrace.Span(name="active-span")
    mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
    return_value = tracing.set_tags({"foo": b"bar"})

    # bytes cast to str in Python 3, unicode in Python 2 (Python 2 not tested)
    # see https://ddtrace.readthedocs.io/en/stable/api.html#ddtrace.Span.set_tag_str
    assert span.get_tag("foo") == str(b"bar")
    assert return_value is None


def test_set_tags_multiple_string_tags(mocker):
    span = ddtrace.Span(name="active-span")
    mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
    tags = {"foo": "bar", "animal": "cat"}
    return_value = tracing.set_tags(tags)
    assert span.get_tag("foo") == "bar"
    assert span.get_tag("animal") == "cat"
    assert return_value is None


def test_set_tags_multiple_mixed_type_tags(mocker):
    span = ddtrace.Span(name="active-span")
    mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
    tags = {"foo": "bar", "animal": b"cat"}
    return_value = tracing.set_tags(tags)
    assert span.get_tag("foo") == "bar"
    assert span.get_tag("animal") == str(b"cat")
    assert return_value is None


# set_tag


def test_set_tag_single_string_tag(mocker):
    span = ddtrace.Span(name="active-span")
    mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
    return_value = tracing.set_tag(key="foo", value="bar")
    assert span.get_tag("foo") == "bar"
    assert return_value is None


def test_set_tag_single_bytes_tag(mocker):
    span = ddtrace.Span(name="active-span")
    mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
    return_value = tracing.set_tag(key="foo", value=b"bar")
    assert span.get_tag("foo") == str(b"bar")
    assert return_value is None


# set_global_tag


def test_set_global_tag(mocker):
    span = ddtrace.Span(name="root-span")
    mocker.patch("xocto.tracing.ddtrace.tracer.current_root_span", return_value=span)
    return_value = tracing.set_global_tag(key="foo", value="bar")
    assert span.get_tag("foo") == "bar"
    assert return_value is None

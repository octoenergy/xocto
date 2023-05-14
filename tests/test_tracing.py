import ddtrace

from xocto import tracing


class TestSetTags:
    def test_set_tags_single_string_tag(self, mocker):
        span = ddtrace.Span(name="active-span")
        mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
        assert tracing.set_tags({"foo": "bar"}) is None
        assert span.get_tag("foo") == "bar"

    def test_set_tags_single_bytes_tag(self, mocker):
        span = ddtrace.Span(name="active-span")
        mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
        assert tracing.set_tags({"foo": b"bar"}) is None
        # bytes cast to str in Python 3, unicode in Python 2 (Python 2 not tested)
        # see https://ddtrace.readthedocs.io/en/stable/api.html#ddtrace.Span.set_tag_str
        assert span.get_tag("foo") == str(b"bar")

    def test_set_tags_multiple_string_tags(self, mocker):
        span = ddtrace.Span(name="active-span")
        mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
        tags = {"foo": "bar", "animal": "cat"}
        assert tracing.set_tags(tags) is None
        assert span.get_tag("foo") == "bar"
        assert span.get_tag("animal") == "cat"

    def test_set_tags_multiple_mixed_type_tags(self, mocker):
        span = ddtrace.Span(name="active-span")
        mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
        tags = {"foo": "bar", "animal": b"cat"}
        assert tracing.set_tags(tags) is None
        assert span.get_tag("foo") == "bar"
        assert span.get_tag("animal") == str(b"cat")


class TestSetTag:
    def test_set_tag_single_string_tag(self, mocker):
        span = ddtrace.Span(name="active-span")
        mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
        assert tracing.set_tag(key="foo", value="bar") is None
        assert span.get_tag("foo") == "bar"

    def test_set_tag_single_bytes_tag(self, mocker):
        span = ddtrace.Span(name="active-span")
        mocker.patch("xocto.tracing.ddtrace.tracer.current_span", return_value=span)
        assert tracing.set_tag(key="foo", value=b"bar") is None
        assert span.get_tag("foo") == str(b"bar")


class TestSetGlobalTag:
    def test_set_global_tag(self, mocker):
        span = ddtrace.Span(name="root-span")
        mocker.patch("xocto.tracing.ddtrace.tracer.current_root_span", return_value=span)
        assert tracing.set_global_tag(key="foo", value="bar") is None
        assert span.get_tag("foo") == "bar"

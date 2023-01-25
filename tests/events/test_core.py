import collections

from xocto.events import core


def test_basic_request_meta(rf):
    request = rf.get("/")
    meta = core._request_meta(request)
    assert "ip_address" in meta


def test_request_meta_includes_user_agent_if_set(rf):
    request = rf.get("/", HTTP_USER_AGENT="xxx")
    meta = core._request_meta(request)
    assert meta["user_agent"] == "xxx"


Session = collections.namedtuple("Session", "session_key")


def test_request_meta_includes_session_key_if_set(rf):
    request = rf.get("/")
    request.session = Session(session_key="x")
    meta = core._request_meta(request)
    assert meta["session"] == "x"

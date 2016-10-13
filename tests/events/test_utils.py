from xocto.events import utils


def test_timer():
    with utils.Timer() as t:
        pass
    assert 0 < t.duration_in_ms < 1

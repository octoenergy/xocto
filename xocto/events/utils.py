import time

__all__ = ["Timer"]


class Timer(object):
    """
    Context manager to allow easy timing of events.
    """

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.duration_in_ms = (self.end - self.start) * 1000

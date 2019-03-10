from functools import wraps
from datetime import timedelta, datetime
import time


class throttle(object):
    def __init__(self, s=1):
        self.throttle_period = s
        self.time_of_last_call = time.time()

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            now = time.time()
            time_since_last_call = now - self.time_of_last_call

            if time_since_last_call > self.throttle_period:
                self.time_of_last_call = now
                return fn(*args, **kwargs)

        return wrapper

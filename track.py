"""
Central location for emitting metrics. Everything here can be configured so that metrics are only
reported under certain conditions (e.g. dev vs. production). They can also be abstracted to report
to a service such as Etsy's StatsD or Datadog
"""

import time
import redis

rclient = redis.StrictRedis(host='localhost', port=6379, db=0)


class track_function_time:
    """Decorator for reporting the time of a function

    :param key: The metric key to report

    Usage:
        >>> @track_function_time('unique.function.key')
        >>> def my_long_function(*args, **kwargs):
        >>>     time.sleep(1000)
        >>>     return True
    """

    def __init__(self, key):
        self.key = key

    def __call__(self, fn):

        def timed(*args, **kwargs):
            ts = time.time()
            val = fn(*args, **kwargs)
            te = time.time()

            elapsed = te - ts
            rclient.lpush(self.key, elapsed)

            return val
        return timed
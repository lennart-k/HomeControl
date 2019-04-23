from typing import Callable
import asyncio
from collections import defaultdict


class TickEngine:
    """
    The TickEngine is there to handle every kind of recurring task.
    Using the decorator TickEngine.tick(interval) you can add a task.
    """
    def __init__(self, core):
        self.core = core
        self.intervals = defaultdict(set)
        self.futures = dict()

    def tick(self, interval: int) -> Callable:
        """

        :param interval: Interval in seconds
        :return:
        """

        def _tick(coro) -> Callable:
            self.intervals[interval].add(coro)

            if not interval in self.futures:
                self.futures[interval] = asyncio.run_coroutine_threadsafe(self.do_tick(interval), self.core.loop)
            return coro
        return _tick

    async def do_tick(self, interval):
        while interval in self.intervals:
            for handler in self.intervals[interval]:
                asyncio.run_coroutine_threadsafe(handler(), self.core.loop)
            await asyncio.sleep(interval)

    async def stop(self):
        for future in self.futures.values():
            future.cancel()

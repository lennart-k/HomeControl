from typing import Callable
import asyncio


class TickEngine:
    """
    The TickEngine is there to handle every kind of recurring task.
    Using the decorator TickEngine.tick(interval) you can add a task.
    """

    def __init__(self, core):
        self.core = core
        self.intervals = {}
        self.futures = set()

    def tick(self, interval: int) -> Callable:
        """

        :param interval: Interval in seconds
        :return:
        """

        def _tick(coro) -> Callable:
            if interval not in self.intervals:
                self.intervals[interval] = set()
                self.futures.add(asyncio.run_coroutine_threadsafe(
                    self.do_tick(interval), self.core.loop))
            self.intervals[interval].add(coro)
            return coro
        return _tick

    async def do_tick(self, interval):
        while interval in self.intervals:
            for handler in self.intervals[interval]:
                asyncio.run_coroutine_threadsafe(handler(), self.core.loop)
            await asyncio.sleep(interval)

    async def stop(self):
        for future in self.futures:
            future.cancel()

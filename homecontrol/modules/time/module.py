"""Everything related with time"""

import math
import time
import asyncio


class Timer:
    """A basic timer"""
    float_remaining: float
    last_time: (float, float) = (0, 0)

    async def init(self):
        """Initialise the timer"""
        await self.reset()

    async def start(self):
        """Action: Start"""
        await self.states.update("running", True)
        self.last_time = (time.time(), self.float_remaining)
        asyncio.run_coroutine_threadsafe(self.tick(), loop=self.core.loop)

    async def stop_timer(self):
        """Action: Stop"""
        start_time, start_remaining = self.last_time
        self.float_remaining = start_remaining-time.time()+start_time
        await self.states.update("running", False)

    async def reset(self):
        """Action: Reset"""
        await self.states.update("running", False)
        await self.states.update("time_remaining", self.cfg["seconds"])
        self.float_remaining = self.cfg["seconds"]

    async def set_time(self, seconds: int):
        """Set time"""
        await self.states.update("time_remaining", seconds)
        self.float_remaining = seconds
        self.last_time = (time.time(), self.float_remaining)

    async def add_time(self, seconds: int):
        """Add time to the timer"""
        await self.states.update("time_remaining",
                                 (await self.states.get("time_remaining"))+seconds)
        self.float_remaining = self.remaining()+seconds
        self.last_time = (time.time(), self.float_remaining)

    def remaining(self) -> float:
        """Get the remaining time"""
        now = time.time()
        last_time, last_remaining = self.last_time
        remaining = last_remaining-now+last_time
        self.last_time = (now, remaining)
        return remaining

    async def tick(self):
        """Update the time"""
        if await self.states.get("running"):
            now_remaining = self.remaining()
            await self.states.update("time_remaining", math.ceil(now_remaining))
            if now_remaining <= 0:
                self.core.event_engine.broadcast("timer_over", timer=self)
                await self.reset()
            else:
                await asyncio.sleep(now_remaining%1)
                asyncio.run_coroutine_threadsafe(self.tick(), loop=self.core.loop)

    async def stop(self):
        """Stop the timer item"""
        await self.stop_timer()

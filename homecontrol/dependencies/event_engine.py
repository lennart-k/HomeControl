from typing import List, Callable
import asyncio


class EventEngine:
    def __init__(self, core):
        self.core = core
        self.handlers = {}

    def broadcast(self, event, *args, **kwargs) -> List[asyncio.Future]:
        """
        Broadcast an event
        Every listener is a coroutine that will simply receive *args and **kwargs
        """
        if self.core.start_args.get("verbose"):
            print(f"EVENT: {event}, {args}, {kwargs}")
        return [asyncio.ensure_future(coro(*args, **kwargs), loop=self.core.loop) for coro in
                self.handlers.get(event, set())]

    async def gather(self, event, *args, **kwargs):
        """
        Broadcast an event and return the results
        """
        return await asyncio.gather(
            *[asyncio.ensure_future(coro(*args, **kwargs), loop=self.core.loop) for coro in
              self.handlers.get(event, set())], loop=self.core.loop)

    def trigger(self, trigger, dest, *args, **kwargs) -> asyncio.Future:
        """
        Triggers are similar to events but they are just there to call a method of a module, item or adapter
        """
        if hasattr(dest, trigger):
            return asyncio.ensure_future(getattr(dest, trigger)(*args, **kwargs), loop=self.core.loop)

    def _register(self, event: str, coro) -> Callable:
        """
        Register a coroutine that will be triggered when the event occurs
        Don't worry, every coroutine can only be registered once
        """
        if event not in self.handlers:
            self.handlers[event] = set()
        self.handlers[event].add(coro)
        return coro

    def register(self, event: str) -> Callable:
        """
        Decorator to register event handlers

        :param event:
        :return:
        """
        def _register(coro):
            print(coro, event)
            if event not in self.handlers:
                self.handlers[event] = set()
            self.handlers[event].add(coro)
            return coro
        return _register

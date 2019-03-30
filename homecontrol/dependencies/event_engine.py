from typing import List, Callable, Any
import asyncio
import time
from collections import defaultdict


class Event:
    __slots__ = ["event_type", "data", "time", "kwargs"]

    def __init__(self, event_type: str, data: dict = None, time: int = None, kwargs: dict = None):
        
        self.event_type = event_type
        self.data = data or {}
        self.time = time
        self.kwargs = kwargs or {}

    def __repr__(self) -> str:
        return f"<Event {self.event_type} kwargs={self.kwargs}>  {self.data}"


class EventEngine:
    def __init__(self, core):
        self.core = core
        self.handlers = defaultdict(set)

    def broadcast(self, event_type: str, data: dict = None, **kwargs) -> List[asyncio.Future]:
        """
        Broadcast an event and return the futures
        Every listener is a coroutine that will simply receive event and **kwargs
        Example:

        async def on_event(event: Event, *args, **kwargs):
            return
        """

        data = data or {}
        data.update(kwargs)
        event = Event(event_type, data=data, time=int(time.time()))

        if self.core.start_args.get("verbose"):
            print(f"EVENT: {event}")

        handlers = list(self.handlers.get("*", list())) + list(self.handlers.get(event_type, list()))

        return [asyncio.ensure_future(handler(event, **kwargs), loop=self.core.loop) for handler in handlers]

    def broadcast_threaded(self, event_type: str, data: dict = None, **kwargs) -> List[asyncio.Task]:
        """
        Same as broadcast BUT
        - It returns Futures and not Tasks
        - It uses threads
        """
        data = data or {}
        data.update(kwargs)
        event = Event(event_type, data=data, time=int(time.time()))

        if self.core.start_args.get("verbose"):
            print(f"EVENT: {event}")

        handlers = list(self.handlers.get("*", list())) + list(self.handlers.get(event_type, list()))

        return [asyncio.run_coroutine_threadsafe(handler(event, **kwargs), loop=self.core.loop) for handler in handlers]


    async def gather(self, event_type: str, data: dict = None, **kwargs) -> List[Any]:
        """
        Broadcast an event and return the results
        """
        return await asyncio.gather(*self.broadcast(event_type, data, **kwargs))

    def trigger(self, trigger: str, dest: Any, *args, **kwargs) -> asyncio.Future:
        """
        Triggers are similar to events but they are just there to call a method of a module, item or adapter
        """
        if hasattr(dest, trigger):
            return asyncio.ensure_future(getattr(dest, trigger)(*args, **kwargs), loop=self.core.loop)

    def register(self, event: str) -> Callable:
        """
        Decorator to register event handlers

        :param event:
        :return:
        """
        def _register(coro):
            self.handlers[event].add(coro)
            return coro
        return _register

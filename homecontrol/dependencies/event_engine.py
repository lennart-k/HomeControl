"""EventEngine for HomeControl"""

from contextlib import suppress
from typing import (
    List, Callable, Any, Union
)
import asyncio
import logging
from collections import defaultdict
from datetime import datetime

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Event:
    """Representation for an Event"""

    def __init__(self,
                 event_type: str,
                 data: dict = None,
                 timestamp: int = None,
                 kwargs: dict = None) -> None:

        self.event_type = event_type
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        self.kwargs = kwargs or {}

    def __repr__(self) -> str:
        return f"<Event {self.event_type} kwargs={self.kwargs}>  {self.data}"


class EventEngine:
    """Dispatcher for events"""
    def __init__(self, core) -> None:
        self.core = core
        self.handlers = defaultdict(set)

    def create_event(self,
                     event_type: str,
                     data: dict = None,
                     **kwargs) -> Event:
        """
        Creates an Event to be broadcasted
        """
        data = data or {}
        data.update(kwargs)
        return Event(event_type, data=data, timestamp=datetime.now())

    def get_event_handlers(self, event: Event) -> List:
        """
        Returns a list of handlers for an Event
        """
        return (
            list(self.handlers.get("*", list()))
            + list(self.handlers.get(event.event_type, list()))
        )


    def broadcast(self,  # lgtm [py/similar-function]
                  event_type: str,
                  data: dict = None,
                  **kwargs) -> List[asyncio.Future]:
        """
        Broadcast an event and return the futures

        Every listener is a coroutine that will simply
        receive event and `kwargs`

        Example:
        >>> async def on_event(event: Event, ...):
        >>>     return
        """
        event = self.create_event(event_type, data, **kwargs)

        LOGGER.debug("Event: %s", event)

        return [asyncio.ensure_future(
            handler(event, **kwargs),
            loop=self.core.loop) for handler in self.get_event_handlers(event)]

    def broadcast_threaded(self,  # lgtm [py/similar-function]
                           event_type: str,
                           data: dict = None,
                           **kwargs) -> List[asyncio.Task]:
        """
        Same as broadcast BUT
        - It returns Futures and not Tasks
        - It uses threads
        """
        event = self.create_event(event_type, data, **kwargs)

        LOGGER.debug("Event: %s", event)

        return [asyncio.run_coroutine_threadsafe(
            handler(event, **kwargs),
            loop=self.core.loop) for handler in self.get_event_handlers(event)]

    async def gather(self,
                     event_type: str,
                     data: dict = None,
                     timeout: Union[float, int, None] = None,
                     **kwargs) -> List[Any]:
        """
        Broadcast an event and return the results
        """
        return await asyncio.wait(
            self.broadcast(event_type, data, **kwargs),
            loop=self.core.loop,
            timeout=timeout)

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

    def remove_handler(self, event: str, handler: callable) -> None:
        """
        Removes an event handler
        """
        with suppress(KeyError):
            self.handlers[event].remove(handler)

"""StateEngine module"""

import logging
from typing import Callable, Any
import voluptuous as vol
from homecontrol.dependencies.data_types import types
from homecontrol.dependencies.entity_types import Item
from homecontrol.const import ItemStatus
from homecontrol.exceptions import (
    ItemNotOnlineError
)

LOGGER = logging.getLogger(__name__)


class StateEngine:
    """Holds the states of an item"""
    def __init__(self, item: Item, core, state_defaults: dict = None):
        state_defaults = state_defaults or {}

        self.item = item
        self.core = core
        self.states = {}
        for state_name, details in item.spec.get("states", {}).items():
            default_state = state_defaults.get(
                state_name, details.get("default", None))

            self.states[state_name] = State(
                self,
                default=default_state,
                getter=getattr(item, details.get("getter", ""), None),
                setter=getattr(item, details.get("setter", ""), None),
                poll_function=getattr(
                    item, details.get("poll-function", ""), None),
                schema=details.get("schema", None),
                state_type=types.get(details.get("type", ""), None),
                poll_interval=details.get("poll-interval", None),
                name=state_name
            )

    async def get(self, state: str):
        """Gets an item's state"""
        if state in self.states:
            return await self.states[state].get()

    async def set(self, state: str, value) -> dict:
        """Sets an item's state"""
        if state in self.states:
            return await self.states[state].set(value)

    def check_value(self, state: str, value) -> vol.error.Error:
        """Checks if a value is valid for a state"""
        return self.states[state].check_value(value)

    async def update(self, state: str, value):
        """Called from an item to update its state"""
        if state in self.states:
            return await self.states[state].update(value)

    async def bulk_update(self, **kwargs):
        """Called from an item to update multiple states"""
        for state, value in kwargs.items():
            await self.states[state].update(value)

    async def dump(self) -> dict:
        """Return a JSON serialisable object"""
        return {
            name: await self.states[name].get() for name in self.states
        }


class State:
    """Holds one state of an item"""

    getter: Callable
    setter: Callable
    value: Any
    mutable: bool

    # pylint: disable=too-many-arguments
    def __init__(self,
                 state_engine: StateEngine,
                 default,
                 getter: Callable = None,
                 setter: Callable = None,
                 poll_function: Callable = None,
                 name: str = None,
                 state_type: type = None,
                 schema: dict = None,
                 poll_interval: float = None) -> None:
        self.value = default if not state_type else state_type(*default)
        self.name = name
        self.getter = getter
        self.setter = setter
        self.state_engine = state_engine
        self.schema = vol.Schema(schema) if schema else None
        self.poll_interval = poll_interval
        self.poll_function = poll_function or self.getter
        if self.poll_interval:
            self.state_engine.core.tick_engine.tick(
                self.poll_interval)(self.poll_value)

    async def poll_value(self) -> None:
        """Polls the current state and updates it"""
        if self.state_engine.item.status != ItemStatus.ONLINE:
            return None
        await self.update(await self.poll_function())

    async def get(self):
        """Gets a state"""
        if self.state_engine.item.status != ItemStatus.ONLINE:
            return None
        if self.getter and not self.poll_interval:
            return await self.getter()
        return self.value

    async def set(self, value) -> dict:
        """Sets a state"""
        if self.state_engine.item.status != ItemStatus.ONLINE:
            raise ItemNotOnlineError(self.state_engine.item.identifier)
        if self.schema:  # Apply schema to new value
            value = self.schema(value)
        if self.setter:
            result: dict = await self.setter(value)
            for state, change in result.items():
                self.state_engine.states[state].value = change
            self.state_engine.core.event_engine.broadcast(
                "state_change", item=self.state_engine.item, changes=result)
            LOGGER.debug("State change: %s %s",
                         self.state_engine.item.identifier, result)
            return result
        return {}

    def check_value(self, value) -> vol.error.Error:
        """Checks if a value is valid for a state"""
        if self.schema:
            try:
                self.schema(value)
                return True
            except vol.error.Error as error:
                return error
        return True

    async def update(self, value):
        """Updates a state"""
        if not self.value == value:
            self.value = value
            self.state_engine.core.event_engine.broadcast(
                "state_change", item=self.state_engine.item, changes={
                    self.name: self.value
                })
            LOGGER.debug("State change: %s %s",
                         self.state_engine.item.identifier, {self.name: value})

            return True
        return False

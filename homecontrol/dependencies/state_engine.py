from typing import Callable, Any
import voluptuous as vol
from dependencies.data_types import types
from dependencies.entity_types import Item
from const import (
    NOT_WORKING
)

class StateEngine:
    def __init__(self, item: Item, core, state_defaults: dict = {}):
        self.item = item
        self.core = core
        self.states = {}
        for state_name, details in item.spec.get("state", {}).items():
            default_state = state_defaults.get(state_name, details.get("default", None)) 

            self.states[state_name] = State(self,
                                            default=default_state,
                                            getter=getattr(item, details.get("getter", ""), None),
                                            setter=getattr(item, details.get("setter", ""), None),
                                            schema=details.get("schema", None),
                                            state_type=types.get(details.get("type", ""), None),
                                            name=state_name,
                                            )

    async def get(self, state: str):
        if state in self.states:
            return await self.states[state].get()

    async def set(self, state: str, value) -> dict:
        if state in self.states:
            return await self.states[state].set(value)

    def check_value(self, state: str, value) -> vol.error.Error:
        """
        Checks if a value is valid for a state
        """
        return self.states[state].check_value(value)

    async def update(self, state: str, value):
        if state in self.states:
            return await self.states[state].update(value)

    async def bulk_update(self, **kwargs):
        for state, value in kwargs.items():
            await self.states[state].update(value)

    async def dump(self) -> dict:
        """
        Return a JSON serialisable object
        """
        return {
            name: await self.states[name].get() for name in self.states.keys()
            }


class State:
    getter: Callable
    setter: Callable
    value: Any
    mutable: bool

    def __init__(self, state_engine: StateEngine, default, getter: Callable=None, setter: Callable =None, name: str =None, state_type=None, schema=None):
        self.value = default if not state_type else state_type(*default)
        self.name = name
        self.getter = getter
        self.setter = setter
        self.state_engine = state_engine
        self.schema = vol.Schema(schema) if schema else None

    async def get(self):
        if self.state_engine.item.status == NOT_WORKING:
            return None
        if self.getter:
            return await self.getter()
        return self.value

    async def set(self, value) -> dict:
        if self.schema:  # Apply schema to new value
            value = self.schema(value)
        if self.setter:
            result: dict = await self.setter(value)
            for state, change in result.items():
                self.state_engine.states[state].value = change
            self.state_engine.core.event_engine.broadcast("state_change", item=self.state_engine.item, changes=result)
            return result
        return {}

    def check_value(self, value) -> vol.error.Error:
        """
        Checks if a value is valid for a state
        """
        if self.schema:
            try:
                self.schema(value)
                return True
            except vol.error.Error as e:
                return e
        return True

    async def update(self, value):
        if not self.value == value:
            self.value = value
            self.state_engine.core.event_engine.broadcast("state_change", item=self.state_engine.item, changes={
                self.name: self.value
            })
            return True
        return False

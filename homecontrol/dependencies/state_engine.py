from typing import Callable, Any
import asyncio
from dependencies.data_types import types


class StateEngine:
    def __init__(self, item, core):
        self.item = item
        self.core = core
        self.states = {}
        for state_name, details in item.spec.get("state", {}).items():
            self.states[state_name] = State(self, details.get("default", None),
                                            getter=getattr(item, details.get("getter", ""), None),
                                            setter=getattr(item, details.get("setter", ""), None),
                                            state_type=types.get(details.get("type", ""), None),
                                            name=state_name,
                                            )

    async def get(self, state):
        if state in self.states:
            return await self.states[state].get()

    async def set(self, state, value):
        if state in self.states:
            return await self.states[state].set(value)

    async def update(self, state, value):
        if state in self.states:
            return await self.states[state].update(value)

    async def dump(self):
        """
        Return a JSON serialisable object
        """
        return {
            "item": self.item,
            "states": {
                name: await self.states[name].get() for name in self.states.keys()
            }
        }


class State:
    getter: Callable
    setter: Callable
    value: Any
    mutable: bool

    def __init__(self, state_engine, default, getter=None, setter=None, name=None, state_type=None):
        self.value = default if not state_type else state_type(*default)
        self.name = name
        self.getter = getter
        self.setter = setter
        self.state_engine = state_engine

    async def get(self):
        if self.getter: return await self.getter()
        return self.value

    async def set(self, value) -> dict:
        if self.setter:
            result: dict = await self.setter(value)
            for state, value in result.items():
                self.state_engine.states[state].value = value
            self.state_engine.core.event_engine.broadcast("state_change", item=self.state_engine.item, changes=result)
            return result
        return {}

    async def update(self, value):
        if not self.value == value:
            self.value = value
            self.state_engine.core.event_engine.broadcast("state_change", item=self.state_engine.item, changes={
                self.name: self.value
            })
            return True
        return False
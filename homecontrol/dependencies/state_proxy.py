"""StateProxy module"""
import asyncio
import logging
from types import MethodType
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Union, cast

import voluptuous as vol

from homecontrol.const import ItemStatus
from homecontrol.exceptions import ItemNotOnlineError

if TYPE_CHECKING:
    from homecontrol.dependencies.entity_types import Item
    from homecontrol.core import Core


LOGGER = logging.getLogger(__name__)


class StateDef:
    """A state definition for automatic setup"""

    def __init__(
            self,
            poll_interval: Optional[float] = None,
            default: Any = None,
            default_factory: Callable = None,
            log_state: bool = True) -> None:

        self._poll_interval = poll_interval
        self._default = default_factory() if default_factory else default
        self.log_state = log_state
        self._getter: Optional[Callable] = None
        self._setter: Optional[Callable] = None
        self._schema: Optional[vol.Schema] = None

    def setter(self, schema: Optional[vol.Schema] = None) -> Callable:
        """Decorator to register a setter"""
        def _setter_decorator(setter_method: Callable) -> Callable:
            self._setter = setter_method
            self._schema = schema
            return setter_method
        return _setter_decorator

    def getter(self) -> Callable:
        """Decorator to register a getter"""
        def _getter_decorator(getter_method: Callable) -> Callable:
            self._getter = getter_method
            return getter_method
        return _getter_decorator

    def register_state(
            self,
            state_proxy: "StateProxy",
            name: str,
            item: "Item") -> "State":
        """Generates a State instance and registers it to a StateProxy"""
        state = State(
            state_proxy,
            self._default,
            MethodType(self._getter, item) if self._getter else None,
            MethodType(self._setter, item) if self._setter else None,
            name=name,
            poll_interval=self._poll_interval,
            schema=self._schema,
            log_state=self.log_state
        )
        state_proxy.register_state(state)
        return state

    def inherit(self, cls: type) -> "StateDef":
        """
        Copies the StateDef but redirects getter and setter to an inherited
        item class
        """
        state_def = StateDef(
            poll_interval=self._poll_interval,
            default=self._default,
            log_state=self.log_state
        )
        # pylint: disable=protected-access
        state_def._getter = getattr(
            cls, self._getter.__name__) if self._getter else None
        state_def._setter = getattr(
            cls, self._setter.__name__) if self._setter else None
        state_def._schema = self._schema
        return state_def


class StateProxy:
    """Holds the states of an item"""

    def __init__(
            self, item: "Item", core: "Core",
            state_defaults: Dict[str, Any] = None) -> None:
        state_defaults = state_defaults or {}

        self.item = item
        self.core = core
        self.states = {}

        for name in dir(item):
            state_def: StateDef = getattr(item, name)
            if name in state_defaults:
                # pylint: disable=protected-access
                state_def._default = state_defaults[name]
            if isinstance(state_def, StateDef):
                state_def.register_state(self, name, item)

    def register_state(self, state: "State") -> None:
        """Registers a State instance to the StateProxy"""
        self.states[state.name] = state

    async def get(self, state: str) -> Any:
        """Gets an item's state"""
        if state in self.states:
            return await self.states[state].get()

    async def set(self, state: str, value) -> Dict[str, Any]:
        """Sets an item's state"""
        return await self.states[state].set(value)

    def check_value(self, state: str, value) -> vol.Error:
        """Checks if a value is valid for a state"""
        return self.states[state].check_value(value)

    def update(self, state: str, value) -> bool:
        """Called from an item to update its state"""
        return self.states[state].update(value)

    def bulk_update(self, **kwargs) -> None:
        """Called from an item to update multiple states"""
        for state, value in kwargs.items():
            self.states[state].value = value
        self.core.event_bus.broadcast(
            "state_change", item=self.item, changes=kwargs)
        LOGGER.debug("State change: %s %s", self.item.identifier, kwargs)

    async def dump(self) -> Dict[str, Any]:
        """Return a JSON serialisable object"""
        return {
            name: await self.states[name].get() for name in self.states
        }


class State:
    """Holds one state of an item"""

    getter: Optional[Callable]
    setter: Optional[Callable]
    value: Any
    mutable: bool
    poll_task: Optional[asyncio.Task] = None
    schema: Optional[vol.Schema]

    # pylint: disable=too-many-arguments
    def __init__(self,
                 state_proxy: StateProxy,
                 default,
                 getter: Optional[Callable] = None,
                 setter: Optional[Callable] = None,
                 name: Optional[str] = None,
                 schema: Optional[vol.Schema] = None,
                 poll_interval: Optional[float] = None,
                 log_state: Optional[bool] = True) -> None:
        self.value = default
        self.name = name
        self.getter = getter
        self.setter = setter
        self.state_proxy = state_proxy
        self.loop = self.state_proxy.core.loop
        self.schema = vol.Schema(schema) if schema else None
        self.poll_interval = poll_interval
        self.log_state = log_state
        if self.poll_interval:
            self.poll_task = self.loop.create_task(self.poll_value())

    async def poll_value(self) -> None:
        """Polls the current state and updates it"""
        while True:
            if self.state_proxy.item.status == ItemStatus.ONLINE:
                self.update(await self.getter())
            await asyncio.sleep(cast(float, self.poll_interval))

    async def get(self):
        """Gets a state"""
        if self.state_proxy.item.status != ItemStatus.ONLINE:
            return None
        if self.getter and not self.poll_interval:
            return await self.getter()
        return self.value

    async def set(self, value) -> Dict[str, Any]:
        """Sets a state"""
        if self.state_proxy.item.status != ItemStatus.ONLINE:
            raise ItemNotOnlineError(self.state_proxy.item.identifier)
        if self.schema:  # Apply schema to new value
            # pylint: disable=not-callable
            value = self.schema(value)
        if self.setter:
            result: dict = await self.setter(value)
            for state, change in result.items():
                self.state_proxy.states[state].value = change
            self.state_proxy.core.event_bus.broadcast(
                "state_change", item=self.state_proxy.item, changes=result)
            LOGGER.debug("State change: %s %s",
                         self.state_proxy.item.identifier, result)
            return result
        return {}

    def check_value(self, value) -> Union[bool, vol.Error]:
        """Checks if a value is valid for a state"""
        if self.schema:
            try:
                # pylint: disable=not-callable
                self.schema(value)
                return True
            except vol.Error as error:
                return error
        return True

    def update(self, value) -> bool:
        """Updates a state"""
        if not self.value == value:
            self.value = value
            self.state_proxy.core.event_bus.broadcast(
                "state_change", item=self.state_proxy.item, changes={
                    self.name: self.value
                })
            LOGGER.debug("State change: %s %s",
                         self.state_proxy.item.identifier, {self.name: value})

            return True
        return False

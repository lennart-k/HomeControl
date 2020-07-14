"""
Module containing the entity types
Every new Item or Module will get one of these classes as a base class
"""

import logging
from typing import Callable, Dict, TYPE_CHECKING, Optional

import voluptuous as vol
from homecontrol.const import EVENT_ITEM_STATUS_CHANGED, ItemStatus
from homecontrol.dependencies.state_proxy import StateProxy

if TYPE_CHECKING:
    from homecontrol.core import Core

LOGGER = logging.getLogger(__name__)


class Item:
    """A dummy Item"""
    type: Optional[str]
    identifier: str
    unique_identifier: str
    name: str
    status: ItemStatus = ItemStatus.OFFLINE
    core: "Core"
    cfg: dict
    config_schema: vol.Schema = vol.Schema(object)
    module: Optional["Module"]
    states: StateProxy
    actions: Dict[str, Callable]

    @classmethod
    async def constructor(
            cls, identifier: str, name: str, cfg: dict, state_defaults: dict,
            core: "Core", unique_identifier: str = None) -> "Item":
        """Constructs an item"""
        item = cls()

        item.core = core
        item.identifier = identifier
        item.unique_identifier = unique_identifier or identifier
        item.name = name

        item.cfg = item.config_schema(cfg or {})
        item.status = ItemStatus.OFFLINE

        item.states = StateProxy(
            item, core, state_defaults=state_defaults or {})

        item.actions = {}
        for attribute in dir(item):
            func = getattr(item, attribute)
            if hasattr(func, "action_name"):
                item.actions[getattr(func, "action_name")] = func

        return item

    def __repr__(self) -> str:
        return (f"<Item {self.type} identifier={self.identifier} "
                f"name={self.name}>")

    async def init(self) -> None:
        """Default init method"""
        return

    async def stop(self) -> None:
        """Default stop method"""
        return

    def update_status(self, status: ItemStatus) -> None:
        """Updates the item status and broadcasts an event"""
        previous_status = self.status
        if status is previous_status:
            return
        self.status = status
        self.core.event_engine.broadcast(
            EVENT_ITEM_STATUS_CHANGED, item=self, previous=previous_status)

    async def run_action(self, name: str, *args, **kwargs) -> bool:
        """Runs an action"""
        if name in self.actions:
            result = await self.actions[name](*args, **kwargs)
            if result is False:
                return False
            return True
        return False


class Module:
    """A dummy Module"""
    name: str
    spec: dict
    core: "Core"
    resource_folder: str
    path: str
    item_specs: dict
    mod: "module"

    def __repr__(self) -> str:
        return f"<Module {self.name}>"

    async def init(self) -> None:
        """Default init method"""
        return

    async def stop(self) -> None:
        """Default stop method"""
        return


ModuleDef = Module

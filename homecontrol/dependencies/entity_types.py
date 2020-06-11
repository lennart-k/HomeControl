"""
Module containing the entity types
Every new Item or Module will get one of these classes as a base class
"""

import logging
from typing import TYPE_CHECKING, Optional

import voluptuous as vol
from homecontrol.const import EVENT_ITEM_STATUS_CHANGED, ItemStatus
from homecontrol.dependencies.action_engine import ActionEngine
from homecontrol.dependencies.state_engine import StateEngine

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
    states: StateEngine
    actions: ActionEngine

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

        item.states = StateEngine(
            item, core, state_defaults=state_defaults or {})
        item.actions = ActionEngine(item, core)
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

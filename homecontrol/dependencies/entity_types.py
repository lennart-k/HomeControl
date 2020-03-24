"""
Module containing the entity types
Every new Item or Module will get one of these classes as a base class
"""

from typing import Optional

import logging
import voluptuous as vol
from homecontrol.const import ItemStatus
from homecontrol.dependencies.state_engine import StateEngine
from homecontrol.dependencies.action_engine import ActionEngine


LOGGER = logging.getLogger(__name__)


class Item:
    """A dummy Item"""
    type: Optional[str]
    identifier: str
    name: str
    status: ItemStatus = ItemStatus.OFFLINE
    core: "homecontrol.core.Core"
    cfg: dict
    config_schema: vol.Schema = vol.Schema(object)
    module: Optional["Module"]
    states: StateEngine
    actions: ActionEngine

    @classmethod
    async def constructor(
            cls, identifier: str, name: str, cfg: dict, state_defaults: dict,
            core: "homecontrol.core.Core") -> "Item":
        """Constructs an item"""
        item = cls()

        item.core = core
        item.identifier = identifier
        item.name = name

        item.cfg = item.config_schema(cfg or {})
        item.status = ItemStatus.OFFLINE

        for key, value in list(item.cfg.items()):
            if isinstance(value, str) and value.startswith("i!"):
                item.cfg[key] = core.item_manager.items.get(value[2:], None)

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


class Module:
    """A dummy Module"""
    name: str
    folder_location: str = None
    spec: dict
    core: "homecontrol.core.Core"
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

"""
Module containing the entity types
Every new Item or Module will get one of these classes as a base class
"""

import voluptuous as vol
from homecontrol.const import ItemStatus


ITEM_SCHEMA = vol.Schema({
    vol.Optional("item_type"): str,
    vol.Required("id"): str,
    vol.Required("!type"): "Item"
})
MODULE_SCHEMA = vol.Schema({
    vol.Optional("meta"): str,
    vol.Required("name"): str,
    vol.Required("!type"): "Module"
})


class Item:
    """A dummy Item"""
    type: str
    identifier: str
    name: str
    status: ItemStatus = ItemStatus.OFFLINE
    core: "homecontrol.core.Core"
    _raw_cfg: dict
    spec: dict
    module: "Module"
    dependant_items: set
    dependencies: set
    states: "homecontrol.dependencies.state_engine.StateEngine"
    actions: "homecontrol.dependencies.action_engine.ActionEngine"

    def __repr__(self) -> str:
        return (f"<Item {self.type} identifier={self.identifier}"
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
    items: dict
    spec: dict
    core: "homecontrol.core.Core"
    meta: dict
    resource_folder: str
    path: str
    items: dict
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

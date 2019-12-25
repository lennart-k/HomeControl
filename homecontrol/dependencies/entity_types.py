"""
Module containing the entity types
Every new Item or Module will get one of these classes as a base class
"""

from typing import (
    Optional
)

import logging
import voluptuous as vol
from homecontrol.const import ItemStatus
from homecontrol.dependencies.state_engine import StateEngine
from homecontrol.dependencies.action_engine import ActionEngine


LOGGER = logging.getLogger(__name__)

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
    type: Optional[str]
    identifier: str
    name: str
    status: ItemStatus = ItemStatus.OFFLINE
    core: "homecontrol.core.Core"
    _raw_cfg: dict
    config_schema: vol.Schema
    spec: dict
    module: Optional["Module"]
    dependant_items: set
    dependencies: set
    states: StateEngine
    actions: ActionEngine

    def __init__(
            self,
            identifier: str,
            name: str,
            cfg: dict,
            state_defaults: dict,
            core: "homecontrol.core.Core",
            dependant_items: Optional[set] = None) -> None:
        self.core = core
        self.identifier = identifier
        self.name = name or identifier

        spec_schema = self.spec.get("config-schema")
        if spec_schema:
            if not isinstance(spec_schema, vol.Schema):
                spec_schema = vol.Schema(
                    spec_schema, extra=vol.ALLOW_EXTRA)

            self.config_schema = spec_schema

        self.cfg = self.config_schema(cfg or {}) if self.config_schema else cfg

        self.status = ItemStatus.OFFLINE

        self.dependant_items = dependant_items or set()
        self.dependencies = set()

        # Dependency management  # TODO Refactoring
        for key, value in list(self.cfg.items()):
            if isinstance(value, str):
                if value.startswith("i!"):
                    dependency = self.core.item_manager.items.get(
                        value[2:], None)
                    self.cfg[key] = dependency
                    if dependency:
                        self.dependencies.add(dependency.identifier)
                        dependency.dependant_items.add(self.identifier)
                    else:
                        LOGGER.error(
                            "Item %s depends on item %s which does not exist",
                            self.identifier, value[2:])
                        self.status = ItemStatus.WAITING_FOR_DEPENDENCY

        self.states = StateEngine(
            self, self.core, state_defaults=state_defaults or {})
        self.actions = ActionEngine(self, self.core)

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

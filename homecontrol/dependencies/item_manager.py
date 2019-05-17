"""ItemManager for HomeControl"""

import asyncio
import logging
import voluptuous as vol

from homecontrol.const import (
    WORKING,
    NOT_WORKING,
    STOPPED
)
from homecontrol.dependencies.state_engine import StateEngine
from homecontrol.dependencies.action_engine import ActionEngine
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.validators import ConsistsOf

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    ConsistsOf({
        vol.Required("id"): str,
        vol.Required("type"): str,
        vol.Optional("name"): str,
        vol.Required("cfg", default={}): dict,
        vol.Required("states", default={}): dict
    })
)


class ItemManager:
    """
    ItemManager manages all your stateful items
    and takes care of dependant items when removing one
    """

    def __init__(self, core):
        self.core = core
        self.items = {}
        self.item_specs = {}

    async def init(self) -> None:
        """Initialise the items from configuration"""
        self.cfg = await self.core.cfg.register_domain("items",
                                                       handler=self,
                                                       schema=CONFIG_SCHEMA,
                                                       allow_reload=True)

        for raw_cfg in self.cfg:
            await self.create_from_raw_cfg(raw_cfg)

    async def add_from_module(self, mod_obj) -> None:
        """
        Adds the item specifications of a module to the dict of available ones

        mod_obj: homecontrol.data_types.Module
        """
        for name, spec in mod_obj.spec.get("items", {}).items():
            spec["class"] = type(name, (getattr(mod_obj.mod, name), Item), {})
            spec["module"] = mod_obj
            self.item_specs[f"{mod_obj.name}.{name}"] = spec
            mod_obj.item_specs[name] = spec

    async def remove_item(self, identifier: str) -> None:
        """
        Removes a HomeControl item and disables dependant items

        identifier: str
            The item's identifier
        """
        item = self.items[identifier]
        try:
            await asyncio.gather(*[
                self.core.loop.create_task(dependant_item.stop()) for dependant_item
                in list(item.dependant_items)+[item]
                if hasattr(dependant_item, "stop")
                and not getattr(dependant_item, "status") == STOPPED], return_exceptions=False)
        # pylint: disable=broad-except
        except Exception:
            LOGGER.warning(
                "An error occured when removing an item", exc_info=True)

        for dependant_item in item.dependant_items:
            dependant_item.status = STOPPED
        for dependency in item.depends_on:
            dependency.dependant_items.remove(item)
        del self.items[identifier]
        LOGGER.info("Item %s has been removed", identifier)

    async def create_from_raw_cfg(self,
                                  raw_cfg: dict) -> Item:
        """Creates an Item from raw_cfg"""
        return await self.create_item(
            identifier=raw_cfg["id"],
            name=raw_cfg.get("name"),
            item_type=raw_cfg["type"],
            raw_cfg=raw_cfg,
            cfg=raw_cfg["cfg"],
            state_defaults=raw_cfg["states"]
        )

    # pylint: disable=too-many-arguments
    async def create_item(self,
                          identifier: str,
                          item_type: str,
                          raw_cfg: dict,
                          cfg: dict = None,
                          state_defaults: dict = None,
                          name: str = None) -> Item:
        """
        Creates a HomeControl item

        identifier: str
        item_type: str
            The type of your item consisting of MODULE.CLASS
        raw_cfg: dict
            Raw configuration to check whether the item has to be recreated
            when updating the configuration
        cfg: dict
        state_defaults: dict
            If the initial state cannot be polled on init you can pass a default
        name: str
            How your item should be displayed in the frontend
        """
        if not item_type in self.item_specs:
            LOGGER.error("Item type not found: %s", item_type)
            return
        spec = self.item_specs[item_type]
        item = spec["class"].__new__(spec["class"])
        item.type = item_type
        item.core = self.core
        item._raw_cfg = raw_cfg
        item.spec = spec
        item.module = spec["module"]
        item.status = WORKING
        item.identifier = identifier
        item.name = name or identifier
        item.dependant_items = set()  # Items that will depend on this one
        item.depends_on = set()  # Items this new item depends on
        config = {}

        if spec.get("config_schema"):
            config = vol.Schema(spec["config_schema"])(cfg or {})

        for key, value in list(config.items()):
            if isinstance(value, str):
                if value.startswith("i!"):
                    i = self.items.get(value[2:], None)
                    config[key] = i
                    # The new item being created depends on the other item:
                    # These dependencies matter to remove the items in the correct order
                    if i:
                        item.depends_on.add(i)
                        i.dependant_items.add(item)

                        if i.status == NOT_WORKING:
                            item.status = NOT_WORKING
                    else:
                        item.status = NOT_WORKING

        item.cfg = config
        item.states = StateEngine(
            item, self.core, state_defaults=state_defaults or {})
        item.actions = ActionEngine(item, self.core)
        item.__init__()

        if not item.status == NOT_WORKING:
            init_result = await item.init()

            # pylint: disable=singleton-comparison
            if init_result == False:
                item.status = NOT_WORKING

        self.items[identifier] = item
        spec["module"].items[identifier] = item
        self.core.event_engine.broadcast("item_created", item=item)
        LOGGER.debug("Item created: %s", item.identifier)
        if item.status == NOT_WORKING:
            LOGGER.warning(
                "Item could not be initialised: %s [%s]", identifier, item_type)
            self.core.event_engine.broadcast("item_not_working", item=item)

        return item

    async def apply_new_configuration(self, domain, config):
        """Applies a new configuration"""
        self.cfg = config

        for item in config:
            if item["id"] in self.items and self.items[item["id"]]._raw_cfg == item:
                continue  # Item is unchanged
            if item["id"] in self.items:
                await self.remove_item(item["id"])

            await self.create_from_raw_cfg(item)
        
        LOGGER.info("Applied new item configuration")

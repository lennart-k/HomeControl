"""ItemManager for HomeControl"""

import asyncio
import logging
import voluptuous as vol

from homecontrol.const import ItemStatus
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

    def iter_items_by_id(self, iterable) -> [Item]:
        """Translates item identifiers into item instances"""
        for identifier in iterable:
            if identifier in self.items:
                yield self.items[identifier]

    async def stop_item(self, item: Item, status: ItemStatus = ItemStatus.STOPPED) -> None:
        """Stops an item"""
        print("YIKEASD")
        await item.stop()
        print("YO")
        LOGGER.info("Item %s has been stopped with status %s",
                    item.identifier, status)
        item.status = status
        for dependant_item in self.iter_items_by_id(item.dependant_items):
            item.status = status
        await asyncio.gather(*[
            self.stop_item(dependant_item, ItemStatus.WAITING_FOR_DEPENDENCY)
            for dependant_item
            in self.iter_items_by_id(item.dependant_items)
            if hasattr(dependant_item, "stop")
            and dependant_item.status == ItemStatus.ONLINE
        ], return_exceptions=False)

    async def remove_item(self, identifier: str) -> None:
        """
        Removes a HomeControl item and disables dependant items

        identifier: str
            The item's identifier
        """
        if not identifier in self.items:
            LOGGER.info(
                "Item %s does not exist so it could not be removed", identifier)
            return

        item = self.items[identifier]
        await self.stop_item(item)

        for dependency in self.iter_items_by_id(item.dependencies):
            dependency.dependant_items.remove(item.identifier)

        del self.items[identifier]
        self.core.event_engine.broadcast("item_removed", item=item)
        LOGGER.info("Item %s has been removed", identifier)

    async def create_from_raw_cfg(self,
                                  raw_cfg: dict,
                                  dependant_items=None) -> Item:
        """Creates an Item from raw_cfg"""
        return await self.create_item(
            identifier=raw_cfg["id"],
            name=raw_cfg.get("name"),
            item_type=raw_cfg["type"],
            raw_cfg=raw_cfg,
            cfg=raw_cfg["cfg"],
            state_defaults=raw_cfg["states"],
            dependant_items=dependant_items
        )

    async def recreate_item(self, item: Item, raw_cfg: dict = None) -> Item:
        """Removes and recreates an item"""
        dependant_items = item.dependant_items
        print(dependant_items)
        # pylint: disable=protected-access
        raw_cfg = raw_cfg or item._raw_cfg
        await self.remove_item(item.identifier)
        del item
        await self.create_from_raw_cfg(raw_cfg, dependant_items)

    async def init_item(self, item: Item) -> None:
        """Initialises an item and dependants"""
        LOGGER.debug("Initialising item %s", item.identifier)
        init_result = await item.init()
        print(init_result, item.identifier, item.status, item.dependant_items)
        # pylint: disable=singleton-comparison
        if init_result == False:
            item.status = ItemStatus.OFFLINE
            return
        else:
            item.status = ItemStatus.ONLINE

        for dependant_item in self.iter_items_by_id(item.dependant_items):
            if (dependant_item.status == ItemStatus.WAITING_FOR_DEPENDENCY
                    and all([dependency.status == ItemStatus.ONLINE
                             for dependency
                             in self.iter_items_by_id(dependant_item.dependencies)])):
                await self.init_item(dependant_item)

    # pylint: disable=too-many-arguments
    async def create_item(self,
                          identifier: str,
                          item_type: str,
                          raw_cfg: dict,
                          cfg: dict = None,
                          state_defaults: dict = None,
                          name: str = None,
                          dependant_items: set = None) -> Item:
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
        if item_type not in self.item_specs:
            LOGGER.error("Item type not found: %s", item_type)
            return

        spec = self.item_specs[item_type]
        item = spec["class"].__new__(spec["class"])
        item.type = item_type
        item.core = self.core
        # pylint: disable=protected-access
        item._raw_cfg = raw_cfg
        item.spec = spec
        item.module = spec["module"]
        item.status = ItemStatus.ONLINE
        item.identifier = identifier
        item.name = name or identifier
        # Identifiers of items that will depend on this one
        item.dependant_items = dependant_items or set()
        # Identifiers of items this new item depends on
        item.dependencies = set()
        config = {}

        if spec.get("config_schema"):
            config = vol.Schema(spec["config_schema"])(cfg or {})

        for key, value in list(config.items()):
            if isinstance(value, str):
                if value.startswith("i!"):
                    dependency = self.items.get(value[2:], None)
                    config[key] = dependency
                    if dependency:
                        item.dependencies.add(dependency.identifier)
                        dependency.dependant_items.add(item.identifier)

                        if dependency.status != ItemStatus.ONLINE:
                            item.status = ItemStatus.WAITING_FOR_DEPENDENCY
                    else:
                        LOGGER.error("Item %s depends on item %s which does not exist",
                                     item.identifier, value[2:])
                        item.status = ItemStatus.WAITING_FOR_DEPENDENCY

        item.cfg = config
        item.states = StateEngine(
            item, self.core, state_defaults=state_defaults or {})
        item.actions = ActionEngine(item, self.core)
        item.__init__()

        self.items[identifier] = item
        spec["module"].items[identifier] = item

        if item.status == ItemStatus.ONLINE:
            await self.init_item(item)

        self.core.event_engine.broadcast("item_created", item=item)
        LOGGER.debug("Item created: %s", item.identifier)
        if item.status != ItemStatus.ONLINE:
            LOGGER.warning(
                "Item could not be initialised: %s [%s]", identifier, item_type)
            self.core.event_engine.broadcast("item_not_working", item=item)

        return item

    async def apply_new_configuration(self, domain, config):
        """Applies a new configuration"""
        self.cfg = config

        for raw_cfg in config:
            # pylint: disable=protected-access
            if raw_cfg["id"] in self.items and self.items[raw_cfg["id"]]._raw_cfg == raw_cfg:
                continue  # Item is unchanged
            if raw_cfg["id"] in self.items:
                await self.recreate_item(self.items[raw_cfg["id"]], raw_cfg)
            else:
                await self.create_from_raw_cfg(raw_cfg)

        LOGGER.info("Applied new item configuration")

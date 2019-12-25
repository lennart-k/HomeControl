"""ItemManager for HomeControl"""

import asyncio
import logging
import voluptuous as vol

from homecontrol.const import ItemStatus
from homecontrol.dependencies.entity_types import Item

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema([
    vol.Schema({
        vol.Required("id"): str,
        vol.Required("type"): str,
        vol.Optional("name"): str,
        vol.Required("states", default={}): dict
    }, extra=vol.ALLOW_EXTRA)
])


class ItemManager:
    """
    ItemManager manages all your stateful items
    and takes care of dependant items when removing one
    """

    def __init__(self, core):
        self.core = core
        self.items = {}
        self.item_classes = {}

    async def init(self) -> None:
        """Initialise the items from configuration"""
        self.cfg = await self.core.cfg.register_domain(
            "items",
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
            item_type = f"{mod_obj.name}.{name}"
            item_class = type(name, (getattr(mod_obj.mod, name), Item), {})
            item_class.spec = spec
            item_class.module = mod_obj
            item_class.type = item_type
            self.item_classes[item_type] = item_class

    def iter_items_by_id(self, iterable) -> [Item]:
        """Translates item identifiers into item instances"""
        for identifier in iterable:
            if identifier in self.items:
                yield self.items[identifier]

    async def stop_item(self,
                        item: Item,
                        status: ItemStatus = ItemStatus.STOPPED) -> None:
        """Stops an item"""
        await item.stop()
        LOGGER.info("Item %s has been stopped with status %s",
                    item.identifier, status)
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
        if identifier not in self.items:
            LOGGER.info(
                "Item %s does not exist so it could not be removed",
                identifier)
            return

        item = self.items[identifier]
        if item.status == ItemStatus.ONLINE:
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
            cfg=raw_cfg.get("cfg", raw_cfg),
            state_defaults=raw_cfg["states"],
            dependant_items=dependant_items
        )

    async def recreate_item(self, item: Item, raw_cfg: dict = None) -> Item:
        """Removes and recreates an item"""
        dependant_items = item.dependant_items
        # pylint: disable=protected-access
        raw_cfg = raw_cfg or item._raw_cfg
        await self.remove_item(item.identifier)
        del item
        await self.create_from_raw_cfg(raw_cfg, dependant_items)

    async def init_item(self, item: Item) -> None:
        """Initialises an item and dependants"""
        LOGGER.debug("Initialising item %s", item.identifier)
        try:
            init_result = await item.init()
        except Exception:  # pylint: disable=broad-except
            LOGGER.warning("An exception was raised when initialising item %s",
                           item.identifier,
                           exc_info=True)
            init_result = False
        # pylint: disable=singleton-comparison
        if init_result == False:  # noqa: E712
            item.status = ItemStatus.OFFLINE
            return

        item.status = ItemStatus.ONLINE

        for dependant_item in self.iter_items_by_id(item.dependant_items):
            if (dependant_item.status == ItemStatus.WAITING_FOR_DEPENDENCY
                    and all([dependency.status == ItemStatus.ONLINE
                             for dependency
                             in self.iter_items_by_id(
                                 dependant_item.dependencies)])):
                await self.init_item(dependant_item)

    # pylint: disable=too-many-arguments,too-many-locals
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

        Args:
            identifier (str):
                The item identifier
            item_type (str):
                The type of your item consisting of MODULE.CLASS
            raw_cfg (dict):
                Raw configuration to check whether the item has to be recreated
                when updating the configuration
            cfg (dict):
                The item's configuration
            state_defaults (dict):
                If the initial state cannot be polled on init
                you can pass a default
            name (str):
                How your item should be displayed in the frontend

        """
        if item_type not in self.item_classes:
            LOGGER.error("Item type not found: %s", item_type)
            return

        item_class = self.item_classes[item_type]

        item = item_class(
            identifier, name, cfg,
            state_defaults=state_defaults,
            core=self.core
        )
        # pylint: disable=protected-access
        item._raw_cfg = raw_cfg

        self.items[identifier] = item
        item_class.module.items[identifier] = item

        if item.status != ItemStatus.WAITING_FOR_DEPENDENCY:
            await self.init_item(item)

        self.core.event_engine.broadcast("item_created", item=item)
        LOGGER.debug("Item created: %s", item.identifier)
        if item.status != ItemStatus.ONLINE:
            LOGGER.warning(
                "Item could not be initialised: %s [%s]",
                identifier, item_type)
            self.core.event_engine.broadcast("item_not_working", item=item)

        return item

    async def apply_new_configuration(self, domain: str, config: dict) -> None:
        """Applies a new configuration"""
        self.cfg = config

        for raw_cfg in config:
            # pylint: disable=protected-access
            if (raw_cfg["id"] in self.items
                    and self.items[raw_cfg["id"]]._raw_cfg == raw_cfg
                    and self.items[raw_cfg["id"]].status != ItemStatus.OFFLINE
               ):  # noqa: E124
                continue  # Item is unchanged
            if raw_cfg["id"] in self.items:
                await self.recreate_item(self.items[raw_cfg["id"]], raw_cfg)
            else:
                await self.create_from_raw_cfg(raw_cfg)

        LOGGER.info("Applied new item configuration")

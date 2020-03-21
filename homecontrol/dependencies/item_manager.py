"""ItemManager for HomeControl"""

import asyncio
from inspect import isclass
import logging
import voluptuous as vol

from homecontrol.const import (
    ItemStatus,
    EVENT_ITEM_CREATED,
    EVENT_ITEM_REMOVED,
    EVENT_ITEM_NOT_WORKING
)
from homecontrol.dependencies.entity_types import Item, Module

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
    """

    def __init__(self, core):
        self.core = core
        self.items = {}
        self.item_constructors = {}

    async def init(self) -> None:
        """Initialise the items from configuration"""
        self.cfg = await self.core.cfg.register_domain(
            "items", schema=CONFIG_SCHEMA)

        for raw_cfg in self.cfg:
            await self.create_from_raw_cfg(raw_cfg)

    async def add_from_module(self, mod_obj: Module) -> None:
        """
        Adds the item specifications of a module to the dict of available ones

        mod_obj: homecontrol.data_types.Module
        """
        for attribute in dir(mod_obj.mod):
            item_class = getattr(mod_obj.mod, attribute)

            if (isclass(item_class)
                    and issubclass(item_class, Item)
                    and item_class is not Item):
                item_class.module = mod_obj
                item_class.type = f"{mod_obj.name}.{item_class.__name__}"
                self.item_constructors[
                    item_class.type] = item_class.constructor

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

    async def remove_item(self, identifier: str) -> None:
        """
        Removes a HomeControl item

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

        del self.items[identifier]
        self.core.event_engine.broadcast(EVENT_ITEM_REMOVED, item=item)
        LOGGER.info("Item %s has been removed", identifier)

    async def create_from_raw_cfg(
            self, raw_cfg: dict) -> Item:
        """Creates an Item from raw_cfg"""
        return await self.create_item(
            identifier=raw_cfg["id"],
            name=raw_cfg.get("name"),
            item_type=raw_cfg["type"],
            raw_cfg=raw_cfg,
            cfg=raw_cfg.get("cfg", raw_cfg),
            state_defaults=raw_cfg["states"]
        )

    async def recreate_item(self, item: Item, raw_cfg: dict = None) -> Item:
        """Removes and recreates an item"""
        # pylint: disable=protected-access
        raw_cfg = raw_cfg or item._raw_cfg
        await self.remove_item(item.identifier)
        del item
        await self.create_from_raw_cfg(raw_cfg)

    async def init_item(self, item: Item) -> None:
        """Initialises an item"""
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

    def register_item(self, item: Item) -> None:
        """
        Registers an item
        """
        self.items[item.identifier] = item

    # pylint: disable=too-many-arguments,too-many-locals
    async def create_item(
            self, identifier: str, item_type: str, raw_cfg: dict,
            cfg: dict = None, state_defaults: dict = None, name: str = None
    ) -> Item:
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
        if item_type not in self.item_constructors:
            LOGGER.error("Item type not found: %s", item_type)
            return

        item_constructor = self.item_constructors[item_type]

        item = await item_constructor(
            identifier, name, cfg,
            state_defaults=state_defaults,
            core=self.core
        )

        self.items[identifier] = item

        await self.init_item(item)

        self.core.event_engine.broadcast(EVENT_ITEM_CREATED, item=item)
        LOGGER.debug("Item created: %s", item.identifier)
        if item.status != ItemStatus.ONLINE:
            LOGGER.warning(
                "Item could not be initialised: %s [%s]",
                identifier, item_type)
            self.core.event_engine.broadcast(EVENT_ITEM_NOT_WORKING, item=item)

        return item

"""ItemManager for HomeControl"""
import asyncio
import logging
from inspect import isclass
from typing import Dict, Iterator, TYPE_CHECKING, List, Optional, cast

import voluptuous as vol
from attr import asdict, attrib, attrs

from homecontrol.const import (EVENT_ITEM_CREATED, EVENT_ITEM_NOT_WORKING,
                               EVENT_ITEM_REMOVED, ItemStatus)
from homecontrol.dependencies.entity_types import Item, Module
from homecontrol.dependencies.storage import Storage

if TYPE_CHECKING:
    from homecontrol.core import Core

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema([
    vol.Schema({
        vol.Required("id"): str,
        vol.Required("type"): str,
        vol.Optional("name"): str,
        vol.Optional("cfg"): dict,
        vol.Required("states", default={}): dict,
        vol.Required("enabled", default=True): bool
    }, extra=vol.ALLOW_EXTRA)
])


# pylint: disable=too-few-public-methods
@attrs(slots=True)
class StorageEntry:
    """The storage representation of an item"""
    unique_identifier: str = attrib()
    type: str = attrib()
    provider: str = attrib()
    enabled: bool = attrib(default=True)
    identifier: str = attrib(default=None)
    state_defaults: dict = attrib(factory=lambda: {})
    cfg: dict = attrib(factory=lambda: {})
    name: str = attrib(default=None)
    hidden: bool = attrib(default=False)

    def __attrs_post_init__(self):
        self.identifier = self.identifier or self.unique_identifier
        self.name = self.name or self.identifier


def yaml_entry_to_storage_entry(yaml_entry: dict) -> StorageEntry:
    """Converts a yaml entry to a JSON entry"""
    if "cfg" in yaml_entry:
        cfg = yaml_entry["cfg"]
    else:
        cfg = yaml_entry.copy()
        for key in ("id", "type", "name", "states", "enabled"):
            cfg.pop(key, None)
    return StorageEntry(
        cfg=cfg,
        enabled=yaml_entry["enabled"],
        identifier=yaml_entry["id"],
        unique_identifier="yaml_" + yaml_entry["id"],
        type=yaml_entry["type"],
        state_defaults=yaml_entry["states"],
        provider="yaml",
        name=yaml_entry.get("name", yaml_entry["id"]),
        hidden=False
    )


class ItemManager:
    """
    ItemManager manages all your stateful items
    """
    core: "Core"
    items: Dict[str, Item]
    yaml_cfg: List[dict]

    def __init__(self, core: "Core"):
        self.core = core
        self.items = {}
        self.item_constructors = {}
        self.storage = Storage(
            self.core, "items", 1,
            storage_init=lambda: {},
            loader=self._load_items,
            dumper=self._dump_items
        )
        self.item_config = self.storage.load_data()

    async def init(self) -> None:
        """Initialise the items from configuration"""
        self.yaml_cfg = cast(List[dict], await self.core.cfg.register_domain(
            "items", schema=CONFIG_SCHEMA, default=[]))
        self.load_yaml_config()

        for storage_entry in self.item_config.values():
            if not storage_entry.enabled:
                continue
            await self.create_from_storage_entry(storage_entry)

    def load_yaml_config(self) -> None:
        """Loads the YAML configuration"""
        for key in tuple(self.item_config.keys()):
            if self.item_config[key].provider == "yaml":
                del self.item_config[key]

        for yaml_entry in self.yaml_cfg:
            storage_entry = yaml_entry_to_storage_entry(yaml_entry)
            self.item_config[
                storage_entry.unique_identifier] = storage_entry
        self.storage.schedule_save(self.item_config)

    def get_storage_entry(self, unique_identifier: str) -> StorageEntry:
        """Returns the StorageEntry for a unique_identifier"""
        return self.item_config.get(unique_identifier, None)

    def update_storage_entry(self, entry: StorageEntry) -> None:
        """Updates a config storage entry"""
        self.item_config[entry.unique_identifier] = entry
        self.storage.schedule_save(self.item_config)

    def _load_items(self, data: dict) -> dict:  # pylint: disable=no-self-use
        entries = {}
        for entry in data:
            entries[entry["unique_identifier"]] = StorageEntry(**entry)
        return entries

    def _dump_items(self, data: dict) -> dict:  # pylint: disable=no-self-use
        return [asdict(entry) for entry in data.values()]

    async def add_from_module(self, mod_obj: Module) -> None:
        """
        Adds the item specifications of a module to the dict of available ones

        mod_obj: homecontrol.entity_types.Module
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

    def iter_items_by_id(self, iterable) -> Iterator[Item]:
        """Translates item identifiers into item instances"""
        for identifier in iterable:
            if identifier in self.items:
                yield self.items[identifier]

    def get_by_unique_identifier(
            self, unique_identifier: str) -> Optional[Item]:
        """Returns an item by its unique identifier"""
        for item in self.items.values():
            if item.unique_identifier == unique_identifier:
                return item

    def get_item(self, identifier: str) -> Optional[Item]:
        """Returns an item by identifier or unique_identifier"""
        return (self.items.get(identifier, None)
                or self.get_by_unique_identifier(identifier))

    async def stop_item(
            self, item: Item, status: ItemStatus = ItemStatus.STOPPED) -> None:
        """Stops an item"""
        if item.status is not ItemStatus.ONLINE:
            return
        await item.stop()
        LOGGER.info("Item %s has been stopped with status %s",
                    item.identifier, status)
        item.status = status

    async def stop(self) -> None:
        """Stops every item"""
        await asyncio.gather(*(
            self.stop_item(item)
            for item in self.items.values()))

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
        self.core.event_bus.broadcast(EVENT_ITEM_REMOVED, item=item)
        LOGGER.info("Item %s has been removed", identifier)

    async def create_from_storage_entry(
            self, storage_entry: StorageEntry) -> Optional[Item]:
        """Creates an Item from a storage entry"""
        return await self.create_item(
            identifier=storage_entry.identifier,
            unique_identifier=storage_entry.unique_identifier,
            name=storage_entry.name,
            item_type=storage_entry.type,
            cfg=storage_entry.cfg,
            state_defaults=storage_entry.state_defaults
        )

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

    async def register_entry(
            self, storage_entry: StorageEntry,
            override: bool = False) -> Optional[Item]:
        """Registers a storage entry"""
        existing_item = self.get_by_unique_identifier(
            storage_entry.unique_identifier)
        existing_entry = self.item_config.get(storage_entry.unique_identifier)

        if not override and existing_entry:
            return existing_item

        if existing_item:
            await self.remove_item(existing_item.identifier)
            storage_entry.enabled = bool(existing_item)

        self.item_config[storage_entry.unique_identifier] = storage_entry
        self.storage.schedule_save(self.item_config)

        if storage_entry.enabled:
            return await self.create_from_storage_entry(storage_entry)

    # pylint: disable=too-many-arguments,too-many-locals
    async def create_item(
            self, identifier: str, item_type: str,
            cfg: dict = None, state_defaults: dict = None, name: str = None,
            unique_identifier: str = None
    ) -> Optional[Item]:
        """Creates a HomeControl item"""
        if item_type not in self.item_constructors:
            LOGGER.error("Item type not found: %s", item_type)
            return

        item_constructor = self.item_constructors[item_type]
        unique_identifier = unique_identifier or identifier

        item = await item_constructor(
            identifier, name, cfg,
            state_defaults=state_defaults,
            core=self.core,
            unique_identifier=unique_identifier
        )

        await self.register_item(item)
        return item

    async def register_item(self, item: Item) -> None:
        """Registers and initialises an already HomeControl item"""
        self.items[item.identifier] = item

        await self.init_item(item)

        self.core.event_bus.broadcast(EVENT_ITEM_CREATED, item=item)
        LOGGER.debug("Item registered: %s", item.unique_identifier)
        if item.status != ItemStatus.ONLINE:
            LOGGER.warning(
                "Item could not be initialised: %s [%s]",
                item.unique_identifier, item.type)
            self.core.event_bus.broadcast(EVENT_ITEM_NOT_WORKING, item=item)

"""ItemManager for HomeControl"""
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
from homecontrol.dependencies.storage import Storage

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


def yaml_entry_to_json(yaml_entry: dict) -> dict:
    """Converts a yaml entry to a JSON entry"""
    if "cfg" in yaml_entry:
        cfg = yaml_entry["cfg"]
    else:
        cfg = yaml_entry.copy()
        for key in ("id", "type", "name", "states", "enabled"):
            cfg.pop(key, None)
    return {
        "type": yaml_entry["type"],
        "name": yaml_entry.get("name", yaml_entry["id"]),
        "unique_identifier": yaml_entry["id"],
        "identifier": yaml_entry["id"],
        "provider": "yaml",
        "enabled": yaml_entry["enabled"],
        "cfg": cfg,
        "state_defaults": yaml_entry["states"],
    }


class ItemManager:
    """
    ItemManager manages all your stateful items
    """

    def __init__(self, core):
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
        self.yaml_cfg = await self.core.cfg.register_domain(
            "items", schema=CONFIG_SCHEMA)
        self.load_yaml_config()

        for storage_entry in self.item_config.values():
            await self.create_from_storage_entry(storage_entry)

    def load_yaml_config(self) -> None:
        """Loads the YAML configuration"""
        for key in tuple(self.item_config.keys()):
            if self.item_config[key]["provider"] == "yaml":
                del self.item_config[key]

        for yaml_entry in self.yaml_cfg:
            json_entry = yaml_entry_to_json(yaml_entry)
            self.item_config[json_entry["unique_identifier"]] = json_entry
        self.storage.schedule_save(self.item_config)

    def update_storage_entry(self, entry: dict) -> None:
        """Updates a config storage entry"""
        self.item_config[entry["unique_identifier"]] = entry
        self.storage.schedule_save(self.item_config)

    def _load_items(self, data: dict) -> dict:
        entries = {}
        for entry in data:
            entries[entry["unique_identifier"]] = entry
        return entries

    def _dump_items(self, data: dict) -> dict:
        return list(data.values())

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

    async def create_from_storage_entry(self, storage_entry: dict) -> Item:
        """Creates an Item from a storage entry"""
        return await self.create_item(
            identifier=storage_entry["identifier"],
            name=storage_entry["name"],
            item_type=storage_entry["type"],
            cfg=storage_entry["cfg"],
            state_defaults=storage_entry["state_defaults"]
        )

    async def init_item(self, item: Item) -> None:
        """Initialises an item"""
        LOGGER.debug("Initialising item %s", item.identifier)
        try:
            init_result = await item.init()
        except:  # pylint: disable=broad-except
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
            self, identifier: str, item_type: str,
            cfg: dict = None, state_defaults: dict = None, name: str = None
    ) -> Item:
        """Creates a HomeControl item"""
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

"""ESPHome integration"""
import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, cast

import aioesphomeapi.model
import voluptuous as vol
from aioesphomeapi import APIClient
from aioesphomeapi.core import APIConnectionError
from aioesphomeapi.model import DeviceInfo, EntityInfo, EntityState
from attr import asdict, attrib, attrs

from homecontrol.const import VERSION_STRING
from homecontrol.dependencies.entity_types import Item, ItemStatus
from homecontrol.dependencies.state_proxy import StateDef, StateProxy
from homecontrol.dependencies.storage import Storage

from .entities import ENTITY_TYPES, ESPHomeItem

if TYPE_CHECKING:
    from homecontrol.core import Core


LOGGER = logging.getLogger(__name__)


@attrs(slots=True)
class StorageEntity:
    """Data model for an entity"""
    entity: EntityInfo = attrib()
    entity_type: str = attrib()


@attrs(slots=True)
class StorageConfig:
    """Data model for storage configuration"""
    device_info: DeviceInfo = attrib()
    entities: List[StorageEntity] = attrib(factory=lambda: [])


class ESPHomeDevice(Item):
    """The ESPHome device"""
    config_schema = vol.Schema({
        vol.Required("host"): str,
        vol.Required("port", default=6053): int,
        vol.Required("password"): str
    })
    api: APIClient
    entities: Dict[int, ESPHomeItem]

    async def connect(self, tries: int = 0) -> None:
        """Tries to connect to the esphome device"""
        try:
            await self.api.connect(
                login="password" in self.cfg, on_stop=self.on_disconnect)
            await self.api.subscribe_states(self.state_callback)
            self.update_status(ItemStatus.ONLINE)
        except APIConnectionError as error:
            self.update_status(ItemStatus.OFFLINE)
            tries = min(tries, 60)
            LOGGER.error("Could not connect to %s, %s. Trying again in %ss",
                         self.identifier, error, tries)
            await asyncio.sleep(tries)
            await self.connect(tries + 1)

    def load_config(self, data: dict) -> StorageConfig:
        """Loads the storage configuration"""
        return StorageConfig(
            entities=[
                StorageEntity(
                    entity=getattr(
                        aioesphomeapi.model, entity_entry["entity_type"])(
                            **entity_entry["entity"]),
                    entity_type=entity_entry["entity_type"]
                )
                for entity_entry in data.get("entities", [])
            ],
            device_info=DeviceInfo(**data.get("device_info", {}))
        )

    def dump_config(self, data: StorageConfig) -> dict:
        """Dumps the storage configuration"""
        return {
            "entities": [asdict(entity) for entity in data.entities],
            "device_info": asdict(data.device_info)
        }

    async def on_disconnect(self) -> None:
        """Handles connection loss"""
        LOGGER.warning("Disconnected from %s, reconnecting.", self.identifier)
        self.update_status(ItemStatus.OFFLINE)
        self.core.loop.create_task(self.connect())

    def update_status(self, status: ItemStatus) -> None:
        super().update_status(status)
        for entity in self.entities.values():
            entity.update_status(status)

    @classmethod
    async def constructor(
            cls, identifier: str, name: str, cfg: Dict[str, Any],
            state_defaults: Dict[str, Any], core: "Core",
            unique_identifier: str) -> "Item":

        cfg = cast(Dict[str, Any], cls.config_schema(cfg or {}))

        item = cls()
        item.entities = {}
        item.core = core
        item.identifier = identifier
        item.unique_identifier = unique_identifier
        item.name = name
        item.cfg = cfg

        item.actions = {}

        item.states = StateProxy(item, core)
        item.status = ItemStatus.OFFLINE

        storage = Storage(core, f"item_data/{unique_identifier}", 1,
                          storage_init=lambda: {},
                          loader=item.load_config,
                          dumper=item.dump_config)

        storage_data: StorageConfig = storage.load_data()

        api = APIClient(
            core.loop, cfg["host"], cfg["port"], cfg["password"],
            client_info=f"HomeControl {VERSION_STRING}"
        )
        item.api = api

        connected, _ = await asyncio.wait(
            {core.loop.create_task(item.connect())}, timeout=6)

        if connected:
            entities, _ = await api.list_entities_services()
            device_info = await api.device_info()

            storage_data.entities.clear()
            for entity in entities:
                storage_data.entities.append(StorageEntity(
                    entity=entity,
                    entity_type=type(entity).__name__
                ))

            storage.schedule_save(storage_data)

        else:
            entities = [storage_entity.entity
                        for storage_entity in storage_data.entities]
            device_info = storage_data.device_info

        version_state = StateDef(default=device_info.esphome_version)
        version_state.register_state(item.states, "version", item)

        for entity in entities:
            entity_type = ENTITY_TYPES.get(type(entity).__name__)
            if not entity_type:
                LOGGER.info("Did not add entity %s", entity)
                continue
            unique_e_identifier = f"{unique_identifier}_{entity.object_id}"
            entity_identifier = f"{identifier}_{entity.object_id}"
            entity_item = await entity_type.constructor(
                identifier=entity_identifier,
                name=entity.name,
                core=core,
                unique_identifier=unique_e_identifier,
                device=item,
                entity=entity
            )
            item.entities[entity.key] = entity_item

            await core.item_manager.register_item(entity_item)

        return item

    def state_callback(self, state: EntityState) -> None:
        """Handles state updates from esphome"""
        entity_item = self.entities.get(state.key)
        if entity_item:
            entity_item.update_state(state)

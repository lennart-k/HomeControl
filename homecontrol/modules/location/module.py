"""location module"""
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import voluptuous as vol

from homecontrol.dependencies.entity_types import Item, ModuleDef
from homecontrol.dependencies.item_manager import StorageEntry
from homecontrol.dependencies.state_proxy import StateDef

if TYPE_CHECKING:
    from homecontrol.core import Core

LOGGER = logging.getLogger(__name__)

SPEC = {
    "name": "location",
    "description": "Provides a location type"
}

HOME_LOCATION_SCHEMA = vol.Schema({
    "location": {
        vol.Required("longitude"): vol.All(
            vol.Coerce(float), vol.Range(-90, 90)),
        vol.Required("latitude"): vol.All(
            vol.Coerce(float), vol.Range(-180, 180)),
        vol.Optional("elevation", default=0): int,
    }
}, extra=vol.ALLOW_EXTRA)


class Module(ModuleDef):
    """Automatically creates the home location item"""
    async def init(self) -> None:
        try:
            home_location = HOME_LOCATION_SCHEMA(
                self.core.cfg.get("home"))["location"]
        except vol.Error:
            return

        await self.core.item_manager.register_entry(StorageEntry(
            unique_identifier="home_location",
            type="location.Location",
            state_defaults={
                **home_location,
                "accuracy": 0,
                "timestamp": datetime.now().isoformat()
            },
            enabled=True,
            name="Home Location",
            provider="location",
        ), override=True)


class Location(Item):
    """A location item"""
    type = "location.Location"

    longitude = StateDef()
    latitude = StateDef()
    elevation = StateDef()
    accuracy = StateDef()
    source = StateDef()
    timestamp = StateDef()

    @classmethod
    async def constructor(
            cls, identifier: str, name: str, cfg: dict, state_defaults: dict,
            core: "Core", unique_identifier: str = None) -> "Item":
        return await super().constructor(
            identifier, name, cfg, {**cfg, **state_defaults},
            core, unique_identifier)

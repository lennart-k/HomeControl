"""Weather data from met.no"""
import asyncio
import logging
from typing import Dict, Optional

import metno
import voluptuous as vol
from aiohttp import ClientSession

from homecontrol.const import ATTRIBUTION
from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item, ModuleDef
from homecontrol.dependencies.item_manager import StorageEntry
from homecontrol.dependencies.state_proxy import StateDef

LOGGER = logging.getLogger(__name__)

ATTRIBUTION_TEXT = "Data provided by The Norwegian Meteorological Institute"

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
    """The met.no module"""
    async def init(self) -> None:
        await self.core.item_manager.register_entry(StorageEntry(
            unique_identifier="weather_home",
            type="metno.MetnoWeather",
            cfg={"home_location": True},
            enabled=True,
            name="Weather Home"
        ))


class MetnoWeather(Item):
    """The weather item"""
    config_schema = vol.Or(
        vol.Schema({
            vol.Required("longitude", "location"): vol.All(
                vol.Coerce(float), vol.Range(-90, 90)),
            vol.Required("latitude", "location"): vol.All(
                vol.Coerce(float), vol.Range(-180, 180)),
            vol.Optional("elevation", default=0): int,
        }, extra=vol.ALLOW_EXTRA),
        vol.Schema({
            vol.Required("home_location", default=False): True,
        }, extra=vol.ALLOW_EXTRA)
    )

    weather: metno.MetWeatherData
    fetch_data_handle: Optional[asyncio.Handle] = None

    datetime = StateDef()
    condition = StateDef()
    humidity = StateDef()
    pressure = StateDef()
    precipitation = StateDef()
    precipitation_probability = StateDef()
    temperature = StateDef()
    wind_bearing = StateDef()
    wind_speed = StateDef()
    wind_gust = StateDef()
    cloudiness = StateDef()

    metadata = {
        ATTRIBUTION: ATTRIBUTION_TEXT
    }

    def get_location(self) -> Optional[Dict[str, str]]:
        """Returns the configured location"""
        if not self.cfg.get("home_location"):
            return {
                "lon": str(self.cfg["longitude"]),
                "lat": str(self.cfg["latitude"]),
                "msl": str(self.cfg["elevation"])
            }

        home_config = self.core.cfg.get("home", {})
        if not home_config.get("location"):
            return

        home_location = HOME_LOCATION_SCHEMA(home_config)["location"]

        return {
            "lon": str(home_location["longitude"]),
            "lat": str(home_location["latitude"]),
            "msl": str(home_location["elevation"])
        }

    async def init(self) -> Optional[bool]:
        self.client_session = ClientSession(loop=self.core.loop)
        self.location = self.get_location()

        if not self.location:
            return False

        self.weather_data = metno.MetWeatherData(
            self.location,
            self.client_session)
        self.update()

    def update(self):
        """Schedules a weather update"""
        self.core.loop.create_task(self.fetch_data())

    @action("update")
    async def fetch_data(self) -> Optional[bool]:
        """Updates the weather data"""
        if not await self.weather_data.fetching_data():
            return False

        current_weather = self.weather_data.get_current_weather()
        self.states.bulk_update(**current_weather)

    async def stop(self) -> None:
        if self.fetch_data_handle:
            self.fetch_data_handle.cancel()
        await self.client_session.close()

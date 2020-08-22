"""InfluxDB module for data collection"""
import logging
import requests
import voluptuous as vol
from influxdb import InfluxDBClient
from homecontrol.dependencies.entity_types import ModuleDef
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.event_bus import Event

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(vol.Or({
    vol.Required("database", default="homecontrol"): str,
    vol.Required("host", default="localhost"): str,
    vol.Required("port", default=8086): vol.Coerce(int),
    vol.Required("username", default="root"): str,
    vol.Required("password", default="root"): str,
    vol.Required("ssl", default=False): bool,
    vol.Required("retry_count", default=5): int,
    vol.Required("verify_ssl", default=False): bool
}, False))


class Module(ModuleDef):
    """An InfluxDB module"""
    async def init(self) -> None:
        self.cfg = await self.core.cfg.register_domain(
            "influxdb", schema=CONFIG_SCHEMA, default=False)
        if not self.cfg:
            return

        self.influx = InfluxDBClient(
            host=self.cfg["host"],
            port=self.cfg["port"],
            database=self.cfg["database"],
            username=self.cfg["username"],
            password=self.cfg["password"],
            ssl=self.cfg["ssl"],
            verify_ssl=self.cfg["verify_ssl"])

        try:
            await self.core.loop.run_in_executor(
                None, self.influx.create_database, self.cfg["database"])
        except requests.exceptions.ConnectionError:
            return LOGGER.error(
                "Could not connect to InfluxDB at %s:%s",
                self.cfg["host"], self.cfg["port"])
        self.core.event_bus.register("state_change")(self.on_state_change)

    async def on_state_change(
            self, event: Event, item: Item, changes: dict) -> None:
        """Write the new state to InfluxDB"""
        changes = {
            name: value
            for name, value in changes.items()
            if item.states.states[name].log_state
            and type(value) in (str, bool, float, int)
        }
        if not changes:
            return
        data = {
            "measurement": "item_state",
            "tags": {
                "item_identifier": item.identifier,
                "item_unique_identifier": item.unique_identifier
            },
            "time": event.timestamp,
            "fields": changes
        }
        try:
            await self.core.loop.run_in_executor(
                None, self.influx.write_points, [data])
        except requests.exceptions.ConnectionError:
            return LOGGER.error(
                "Could not connect to InfluxDB at %s:%s",
                self.cfg["host"], self.cfg["port"])

    async def stop(self) -> None:
        """Handles a HomeControl shutdown"""
        self.core.event_bus.remove_handler(
            "state_change", self.on_state_change)

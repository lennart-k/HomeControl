"""Bitcoin stats"""
import asyncio

import requests

import voluptuous as vol
from homecontrol.dependencies.action_engine import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_engine import StateDef

SPEC = {
    "name": "Bitcoin",
    "description": "Get statistics about Bitcoin",
}

RESULT_SCHEMA = vol.Schema({
    vol.Required("timestamp"): float,
    vol.Required("market_price_usd"): float,
    vol.Required("hash_rate"): float,
    vol.Required("n_btc_mined"): int,
    vol.Required("minutes_between_blocks"): float
}, extra=vol.ALLOW_EXTRA)

DATA_URL = "https://api.blockchain.info/stats"


class BitcoinStats(Item):
    """Item holding Bitcoin stats"""

    update_task: asyncio.Task
    last_update = StateDef()
    market_price_usd = StateDef()
    hash_rate = StateDef()
    n_btc_mined = StateDef()
    block_interval = StateDef()

    config_schema = vol.Schema({
        vol.Required("update_interval", default=600):
        vol.Coerce(type=int)
    }, extra=vol.ALLOW_EXTRA)

    async def init(self):
        """Initialise the item"""
        self.update_task = self.core.loop.create_task(self.update_interval())

    async def update_interval(self) -> None:
        """Updates the states"""
        while True:
            await self.update_stats()
            await asyncio.sleep(self.cfg["update_interval"])

    async def stop(self) -> None:
        self.update_task.cancel()

    @action("update")
    async def update_stats(self):
        """Update the current states"""
        try:
            result = RESULT_SCHEMA(requests.get(DATA_URL).json())
        except vol.SchemaError:
            return

        self.states.bulk_update(
            last_update=result["timestamp"],
            market_price_usd=result["market_price_usd"],
            hash_rate=result["hash_rate"],
            n_btc_mined=result["n_btc_mined"],
            block_interval=result["minutes_between_blocks"])

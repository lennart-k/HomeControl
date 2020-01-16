"""Bitcoin stats"""

import voluptuous as vol
import requests

from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.action_engine import action
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

    last_update = StateDef()
    market_price_usd = StateDef()
    hash_rate = StateDef()
    n_btc_mined = StateDef()
    block_interval = StateDef()

    config_schema = vol.Schema({
        vol.Required("update_interval", default=3600):
        vol.Coerce(type=int)
    }, extra=vol.ALLOW_EXTRA)

    async def init(self):
        """Initialise the item"""
        self.core.tick_engine.tick(
            self.cfg["update_interval"])(self.update_stats)

    @action("update")
    async def update_stats(self):
        """Update the current states"""
        try:
            result = RESULT_SCHEMA(requests.get(DATA_URL).json())
        except vol.SchemaError:
            return

        await self.states.bulk_update(
            last_update=result["timestamp"],
            market_price_usd=result["market_price_usd"],
            hash_rate=result["hash_rate"],
            n_btc_mined=result["n_btc_mined"],
            block_interval=result["minutes_between_blocks"])

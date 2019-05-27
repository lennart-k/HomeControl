"""Bitcoin stats"""

import voluptuous as vol
import requests

SPEC = {
    "meta": {
        "name": "Bitcoin",
        "description": "Get statistics about Bitcoin"
    },
    "items": {
        "BitcoinStats": {
            "config_schema": vol.Schema({
                vol.Required("update_interval", default=3600):
                vol.Coerce(type=int)
            }),
            "actions": {
                "update": "update_stats"
            },
            "states": {
                "last_update": {"type": float},
                "market_price_usd": {"type": float},
                "hash_rate": {"type": "float"},
                "n_btc_mined": {"type": int},
                "block_interval": {"type": float}
            }
        }
    }
}

RESULT_SCHEMA = vol.Schema({
    vol.Required("timestamp"): float,
    vol.Required("market_price_usd"): float,
    vol.Required("hash_rate"): float,
    vol.Required("n_btc_mined"): int,
    vol.Required("minutes_between_blocks"): float
}, extra=vol.ALLOW_EXTRA)

DATA_URL = "https://api.blockchain.info/stats"


class BitcoinStats:
    """Item holding Bitcoin stats"""
    async def init(self):
        """Initialise the item"""
        tick(self.cfg["update_interval"])(self.update_stats)

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

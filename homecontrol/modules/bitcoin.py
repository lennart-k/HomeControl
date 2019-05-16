import voluptuous as vol
import requests


SPEC = """
meta:
  name: Bitcoin
  description: Get statistics about Bitcoin

items:
  BitcoinStats:
    config_schema:
      !vol/Required { schema: update_interval, default: 3600 }:
        !vol/Coerce { type: !type/int }

    actions:
      update: update_stats

    states:
      last_update:
        type: Float
      market_price_usd:
        type: Float
      hash_rate:
        type: Float
      n_btc_mined:
        type: Integer
      block_interval:
        type: Float

"""

RESULT_SCHEMA = vol.Schema({
    vol.Required("timestamp"): float,
    vol.Required("market_price_usd"): float,
    vol.Required("hash_rate"): float,
    vol.Required("n_btc_mined"): int,
    vol.Required("minutes_between_blocks"): float
}, extra=vol.ALLOW_EXTRA)

DATA_URL = "https://api.blockchain.info/stats"


class BitcoinStats:
    async def init(self):
        tick(self.cfg["update_interval"])(self.update_stats)

    async def update_stats(self):
        try:
            result = RESULT_SCHEMA(requests.get(DATA_URL).json())
        except vol.SchemaError as e:
            return

        await self.states.bulk_update(last_update=result["timestamp"],
                                      market_price_usd=result["market_price_usd"],
                                      hash_rate=result["hash_rate"],
                                      n_btc_mined=result["n_btc_mined"],
                                      block_interval=result["minutes_between_blocks"])

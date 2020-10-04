"""covid module"""
import asyncio
import logging
from typing import Optional

import aiohttp
import voluptuous as vol
from coronavirus import JohnsHopkinsCase, get_cases

from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef

LOGGER = logging.getLogger(__name__)


class CovidStats(Item):
    """covid module"""
    update_task: Optional[asyncio.Task] = None

    confirmed = StateDef()
    deaths = StateDef()
    recovered = StateDef()

    config_schema = vol.Schema({
        vol.Required("country"): str,
        vol.Required("update_interval", default=3600): vol.Coerce(type=int)
    }, extra=vol.ALLOW_EXTRA)

    async def init(self):
        """Initialise the item"""
        self.update_task = self.core.loop.create_task(self.update_interval())
        self.session = aiohttp.ClientSession(loop=self.core.loop)

    async def update_interval(self) -> None:
        """Updates the states"""
        while True:
            await self.update_stats()
            await asyncio.sleep(self.cfg["update_interval"])

    async def stop(self) -> None:
        if self.update_task:
            self.update_task.cancel()
        await self.session.close()

    @action("update")
    async def update_stats(self):
        """Update the current states"""
        results = await get_cases(self.session)
        try:
            result: JohnsHopkinsCase = next(
                filter(lambda result: result.country
                       == self.cfg["country"], results))
            self.states.bulk_update(
                confirmed=result.confirmed,
                deaths=result.deaths,
                recovered=result.recovered
            )
        except StopIteration:
            LOGGER.error("Invalid country: %s", self.cfg["country"])

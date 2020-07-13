"""Module for internet speedtest"""

import logging

import speedtest

from homecontrol.dependencies.action_engine import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef

LOGGER = logging.getLogger(__name__)


class Speedtest(Item):
    """The Speedtest item"""
    download_speed = StateDef()
    upload_speed = StateDef()
    ping = StateDef()

    async def init(self) -> None:
        """Init the Speedtest item"""

    @action("measure")
    async def measure(self) -> None:
        """
        Measures the internetspeed
        Gets called by state polling
        """
        LOGGER.debug("Doing speedtest")
        s = speedtest.Speedtest()  # pylint: disable=invalid-name

        def do_speedtest():
            """Blocking task"""
            s.get_best_server()
            s.download()
            s.upload(pre_allocate=False)

        await self.core.loop.run_in_executor(None, do_speedtest)
        await self.states.bulk_update(
            ping=s.results.ping,
            upload_speed=s.results.upload,
            download_speed=s.results.download
        )

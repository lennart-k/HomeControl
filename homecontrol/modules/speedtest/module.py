"""Module for internet speedtest"""

import logging

import speedtest

LOGGER = logging.getLogger(__name__)


class Speedtest:
    """The Speedtest item"""
    async def init(self) -> None:
        """Init the Speedtest item"""

    async def measure(self) -> None:
        """
        Measures the internetspeed
        Gets called by state polling
        """
        LOGGER.debug("Doing speedtest now")
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

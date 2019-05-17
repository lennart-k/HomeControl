"""The core instance for HomeControl"""

import os
from contextlib import suppress
import signal
import asyncio
import logging

from homecontrol.dependencies.event_engine import EventEngine
from homecontrol.dependencies.module_manager import ModuleManager
from homecontrol.dependencies.item_manager import ItemManager
from homecontrol.dependencies.tick_engine import TickEngine
from homecontrol.dependencies.config_manager import ConfigManager

from homecontrol.const import (
    EXIT_SHUTDOWN,
    EXIT_RESTART
)

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Core:
    """
    Represents the root object for HomeControl
    """

    # pylint: disable=too-many-arguments
    def __init__(self,
                 cfg: dict,
                 cfg_path: str,
                 loop: asyncio.AbstractEventLoop = None,
                 start_args: dict = None,
                 exit_return: int = None) -> None:
        """
        :param cfg: config dictionary
        :param cfg_path: configuration file
        :param loop: asyncio EventLoop
        :param start_args: start parameters
        :param exit_return: Shutdown or Restart on stop
        """
        self.start_args = start_args or {}
        self.loop = loop or asyncio.get_event_loop()
        self.cfg = ConfigManager(cfg, cfg_path)
        self.cfg_path = cfg_path
        self.block_event = asyncio.Event()
        self.tick_engine = TickEngine(core=self)
        self.event_engine = EventEngine(core=self)
        self.module_manager = ModuleManager(core=self)
        self.item_manager = ItemManager(core=self)
        self.exit_return = exit_return or EXIT_SHUTDOWN

    async def bootstrap(self) -> None:
        """
        Startup coroutine for Core
        """
        if not os.name == "nt":  # Windows does not have signals
            self.loop.add_signal_handler(
                signal.SIGINT, lambda: self.loop.create_task(self.stop()))
            self.loop.add_signal_handler(
                signal.SIGTERM, lambda: self.loop.create_task(self.stop()))
        else:
            # Windows needs its special signal handling
            signal.signal(signal.SIGINT, lambda *args: self.loop.create_task(self.stop()))
            signal.signal(signal.SIGTERM, lambda *args: self.loop.create_task(self.stop()))

        # Load modules
        await self.module_manager.init()

        # Init items
        await self.item_manager.init()

        self.event_engine.broadcast("core_bootstrap_complete")
        LOGGER.info("Core bootstrap complete")

    async def block_until_stop(self) -> int:
        """Blocking method to keep HomeControl running until Core.block_event is set"""
        with suppress(asyncio.CancelledError):
            await self.block_event.wait()
        return self.exit_return

    async def stop(self) -> None:
        """
        Stops HomeControl
        Depending on Core.exit_return HomeControl may also automatically be restarted
        """
        await self.tick_engine.stop()
        LOGGER.warning("Shutting Down")

        for module in list(self.module_manager.loaded_modules.keys()):
            await self.module_manager.unload_module(module)
        pending = asyncio.Task.all_tasks(loop=self.loop)

        LOGGER.info("Waiting for pending tasks (1s)")
        await asyncio.wait(pending, loop=self.loop, timeout=1)
        LOGGER.warning("Closing the loop soon")
        self.block_event.set()

    async def restart(self) -> None:
        """Restarts HomeControl"""
        self.exit_return = EXIT_RESTART
        await self.stop()

    async def shutdown(self) -> None:
        """Shuts HomeControl down"""
        self.exit_return = EXIT_SHUTDOWN
        await self.stop()

from contextlib import suppress
import signal
import asyncio
from dependencies.event_engine import EventEngine
from dependencies.module_manager import ModuleManager
from dependencies.entity_manager import EntityManager
from dependencies.logger import Logger
from dependencies.tick_engine import TickEngine

from const import (
    EXIT_SHUTDOWN,
    EXIT_RESTART
)


class Core:
    """
    Represents the root object for HomeControl
    """

    def __init__(self, cfg: dict, loop: asyncio.AbstractEventLoop = None, start_args: dict = None, exit_return: int = None) -> None:
        """

        :param cfg: Config dictionary
        :param loop: asyncio EventLoop
        """
        self.cfg = cfg
        self.start_args = start_args or {}
        self.loop = loop or asyncio.get_event_loop()
        self.block_event = asyncio.Event()
        self.tick_engine = TickEngine(core=self)
        self.event_engine = EventEngine(core=self)
        self.logger = Logger(core=self)
        self.module_manager = ModuleManager(core=self)
        self.entity_manager = EntityManager(core=self)
        self.exit_return = exit_return or EXIT_SHUTDOWN

        self.loop.add_signal_handler(signal.SIGINT, lambda: self.loop.create_task(self.stop()))
        self.loop.add_signal_handler(signal.SIGTERM, lambda: self.loop.create_task(self.stop()))

    async def bootstrap(self) -> None:
        """
        Startup coroutine for Core
        """
        for folder in self.cfg.get("module-manager", {}).get("folders", {}):
            await self.module_manager.load_folder(folder)

        # Create items from config file
        for item in self.cfg["items"]:
            await self.entity_manager.create_item(item["id"], item["type"], item.get("cfg"))

        self.event_engine.broadcast("core_bootstrap_complete")

    async def block_until_stop(self) -> int:
        with suppress(asyncio.CancelledError):
            await self.block_event.wait()
        return self.exit_return

    async def stop(self) -> None:
        await self.tick_engine.stop()
        print("SHUTTING DOWN!")
        
        for module in list(self.module_manager.loaded_modules.keys()):
            await self.module_manager.unload_module(module)
        pending = asyncio.Task.all_tasks(loop=self.loop)
        
        print("Waiting for pending tasks (1s)")
        await asyncio.wait(pending, loop=self.loop, timeout=1)
        print("Closing the loop soon")
        self.block_event.set()
    
    async def restart(self) -> None:
        self.exit_return = EXIT_RESTART
        await self.stop()

    async def shutdown(self) -> None:
        self.exit_return = EXIT_SHUTDOWN
        await self.stop()

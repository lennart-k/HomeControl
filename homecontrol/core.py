import signal
import aiomonitor
from functools import partial
import asyncio
import yaml
from dependencies.entity_discovery import EntityDiscoveryProvider
from dependencies.event_engine import EventEngine
from dependencies.module_manager import ModuleManager
from dependencies.entity_manager import EntityManager
from dependencies.api_server import APIServer
from dependencies.logger import Logger
from dependencies.tick_engine import TickEngine
import sys
from const import (
    EXIT_SHUTDOWN,
    EXIT_RESTART
)


class Core:
    """
    Represents the root object for HomeControl
    """

    def __init__(self, cfg: dict, loop: asyncio.AbstractEventLoop = None, start_args: dict = {}, exit_return: int = None) -> None:
        """

        :param cfg: Config dictionary
        :param loop: asyncio EventLoop
        """
        self.cfg = cfg
        self.start_args = start_args
        self.loop = loop or asyncio.get_event_loop()
        self.block_event = asyncio.Event()
        self.tick_engine = TickEngine(core=self)
        self.event_engine = EventEngine(core=self)
        self.logger = Logger(core=self)
        self.entity_disco = EntityDiscoveryProvider(core=self)
        self.module_manager = ModuleManager(core=self)
        self.entity_manager = EntityManager(core=self)
        self.api_server = APIServer(core=self)
        self.exit_return = exit_return or EXIT_SHUTDOWN

        # signal.signal(signal.SIGTERM, lambda signum, frame: print("Yeee"))
        # signal.signal(signal.SIGINT, lambda signum, frame: self.loop.create_task(self.stop()))
        self.loop.add_signal_handler(signal.SIGINT, lambda: self.loop.create_task(self.stop()))

    async def bootstrap(self) -> None:
        """
        Startup coroutine for Core
        """
        for folder in self.cfg.get("module-manager", {}).get("folders", {}):
            await self.module_manager.load_folder(folder)

        # Create items from config file
        for item in self.cfg["items"]:
            await self.entity_manager.create_item(item["id"], item["type"], item["cfg"])

        @self.event_engine.register("state_change")
        async def on_state_change(item, changes):
            if item.identifier == "Button":
                print(changes["value"])
                await self.entity_manager.items["Relay"].states.set("on", changes["value"])

            if item.identifier == "RGB Strip" and "on" in changes:
                await self.entity_manager.items["LCD"].states.set("line2", f"RGB Strip: {changes['on']}")

            if item.identifier == "Relay":
                await self.entity_manager.items["LCD"].states.set("line1", f"Relay: {changes['on']}")

        @self.event_engine.register("ir_nec_code")
        async def on_code(address, data, edges):
            print(address, data)
            if (address, data) == (32, 64):
                await self.entity_manager.items["Relay"].states.set("on", True)

            elif (address, data) == (32, 192):
                await self.entity_manager.items["Relay"].states.set("on", False)

            elif (address, data) == (32, 16):
                self.blocking_task.cancel()

    async def block_until_stop(self) -> int:
        try:
            await self.block_event.wait()
            # await asyncio.gather(self.blocking_task, loop=self.loop)
        except asyncio.CancelledError:
            pass
        return self.exit_return

    async def stop(self) -> None:
        await self.api_server.stop()
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

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    with aiomonitor.Monitor(loop=loop):
        cfg = yaml.load(open("config.yaml"))
        core = Core(cfg, loop=loop)
        loop.call_soon(partial(loop.create_task, core.bootstrap()))
        loop.run_forever()
    loop.close()

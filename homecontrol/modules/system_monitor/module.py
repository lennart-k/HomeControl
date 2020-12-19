"""system monitor module"""
import asyncio

import psutil

from homecontrol.dependencies.entity_types import Item, ModuleDef
from homecontrol.dependencies.item_manager import StorageEntry
from homecontrol.dependencies.state_proxy import StateDef

SPEC = {
    "name": "System Monitor",
    "description": "Monitor your CPU and memory usage"
}


class Module(ModuleDef):
    """Automatically register SystemMonitor"""
    async def init(self) -> None:
        await self.core.item_manager.register_entry(StorageEntry(
            unique_identifier="system_monitor",
            type="system_monitor.SystemMonitor",
            name="System Monitor"
        ))


class SystemMonitor(Item):
    """The SystemMonitor item"""
    update_job: asyncio.Task

    cpu_count = StateDef(default=psutil.cpu_count())
    cpu_percent = StateDef(default=psutil.cpu_percent(percpu=True))
    memory = psutil.virtual_memory()
    memory_total = StateDef(default=memory.total)
    memory_usage = StateDef(default=memory.used)
    memory_percent = StateDef(default=memory.percent)
    del memory
    swap = psutil.swap_memory()
    swap_total = StateDef(default=swap.total)
    swap_usage = StateDef(default=swap.used)
    swap_percent = StateDef(default=swap.percent)
    del swap

    async def init(self) -> None:
        """Start the update job"""
        self.update_job = self.core.loop.create_task(self.update())

    async def stop(self) -> None:
        """Cancel the update job"""
        self.update_job.cancel()

    async def update(self) -> None:
        """Update the CPU and memory stats every 2 seconds"""
        def _update():
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            self.states.bulk_update(
                cpu_percent=psutil.cpu_percent(percpu=True),
                memory_usage=memory.used,
                memory_percent=memory.percent,
                swap_usage=swap.used,
                swap_percent=swap.percent
            )
        while True:
            await self.core.loop.run_in_executor(None, _update)
            await asyncio.sleep(2)

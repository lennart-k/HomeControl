import asyncio
from netdisco.discovery import NetworkDiscovery
from concurrent.futures import ThreadPoolExecutor


class EntityDiscoveryProvider:
    async def init(self):
        self.net_disco = NetworkDiscovery()

        @tick(30)
        async def discover():
            def discover():
                self.net_disco.scan()
                for device in self.net_disco.discover():
                    if device == "google_cast":
                        for dev in self.net_disco.get_info(dev):
                            pass
                            # await self.google_cast(dev)
                    # self.core.event_engine.broadcast("entity_discovered", device, self.net_disco.get_info(device))
                self.net_disco.stop()

            await self.core.loop.run_in_executor(ThreadPoolExecutor(2), discover)

        self.discover = discover

    async def google_cast(self, info):
        print(info)

    async def stop(self):
        self.core.tick_engine.intervals[30].remove(self.discover)

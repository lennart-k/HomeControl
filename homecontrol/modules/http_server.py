import asyncio
import logging
from aiohttp import web
import os


SPEC = """
meta:
  name: HTTP Server
"""

LOGGER = logging.getLogger(__name__)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


class Module:
    """
    HTTPServer exposes HTTP endpoints for interaction from outside
    """

    async def init(self):
        """
        Sets up an HTTPServer
        """

        self.main_app = web.Application(loop=self.core.loop)
        event("core_bootstrap_complete")(self.start)

    async def start(self, *args):
        self.route_table_def = web.RouteTableDef()
        await self.core.event_engine.gather("http_add_main_routes", router=self.route_table_def)
        await self.core.event_engine.gather("http_add_main_subapps", main_app=self.main_app)

        self.main_app.add_routes(self.route_table_def)
        self.handler = self.main_app.make_handler(loop=self.core.loop)

        # Windows doesn't support reuse_port
        self.future = self.core.loop.create_server(self.handler, self.core.cfg["http-server"]["host"],
                                              self.core.cfg["http-server"]["port"],
                                              reuse_address=True, reuse_port=os.name != "nt")
        asyncio.run_coroutine_threadsafe(self.future, loop=self.core.loop)

    async def stop(self):
        if self.main_app.frozen:
            await self.main_app.cleanup()
            self.future.close()

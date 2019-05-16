"""The http server"""

import asyncio
import os
import logging

from aiohttp import web


SPEC = """
meta:
  name: HTTP Server
"""

LOGGER = logging.getLogger(__name__)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


class Module:
    """The HTTP server module"""
    handler: None
    future: None

    """HTTPServer exposes HTTP endpoints for interaction from outside"""

    async def init(self):
        """Sets up an HTTPServer"""

        self.main_app = web.Application(loop=self.core.loop)
        self.route_table_def = web.RouteTableDef()
        event("core_bootstrap_complete")(self.start)

    async def start(self, *args):
        """Start the HTTP server"""
        await self.core.event_engine.gather("http_add_main_routes", router=self.route_table_def)
        await self.core.event_engine.gather("http_add_main_subapps", main_app=self.main_app)

        self.main_app.add_routes(self.route_table_def)
        self.handler = self.main_app.make_handler(loop=self.core.loop)

        # Windows doesn't support reuse_port
        self.future = self.core.loop.create_server(
            self.handler,
            self.core.cfg["http-server"]["host"],
            self.core.cfg["http-server"]["port"],
            reuse_address=True, reuse_port=os.name != "nt")
        asyncio.run_coroutine_threadsafe(self.future, loop=self.core.loop)

    async def stop(self):
        """Stop the HTTP server"""
        if self.main_app.frozen:
            await self.main_app.cleanup()
            self.future.close()

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
    server: "asyncio.Server"
    route_table_def: web.RouteTableDef
    main_app: web.Application

    """HTTPServer exposes HTTP endpoints for interaction from outside"""

    async def init(self):
        """Sets up an HTTPServer"""

        event("core_bootstrap_complete")(self.start)

    async def start(self, *args):
        """Start the HTTP server"""
        self.main_app = web.Application(loop=self.core.loop)

        self.route_table_def = web.RouteTableDef()

        await self.core.event_engine.gather("http_add_main_routes", router=self.route_table_def)
        await self.core.event_engine.gather("http_add_main_subapps", main_app=self.main_app)

        self.main_app.add_routes(self.route_table_def)
        self.handler = self.main_app.make_handler(loop=self.core.loop)

        # Windows doesn't support reuse_port
        self.server = await self.core.loop.create_server(
            self.handler,
            self.core.cfg["http-server"]["host"],
            self.core.cfg["http-server"]["port"],
            reuse_address=True, reuse_port=os.name != "nt")
        LOGGER.info("Started the HTTP server")

    async def stop(self):
        """Stop the HTTP server"""
        LOGGER.info("Stopping the HTTP server on %s:%s",
                    self.core.cfg["http-server"]["host"],
                    self.core.cfg["http-server"]["port"])
        if self.main_app.frozen:
            await self.main_app.cleanup()
            self.server.close()
            await self.server.wait_closed()

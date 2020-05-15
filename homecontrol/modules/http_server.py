"""The http server"""

import os
import logging
import ssl

import voluptuous as vol
from aiohttp import web

from homecontrol.const import EVENT_CORE_BOOTSTRAP_COMPLETE

SPEC = {
    "name": "HTTP Server"
}

CONFIG_SCHEMA = vol.Schema({
    vol.Required("host", default=None): vol.Any(str, None),
    vol.Required("port", default=8082): vol.Coerce(int),
    vol.Required("ssl", default=False): vol.Any(
        bool,
        {
            "certificate": str,
            "key": str,
        })
})

LOGGER = logging.getLogger(__name__)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


class SSLLogFilter(logging.Filter):
    """Filter ssl.SSLError from logs"""
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter function"""
        return not (record.exc_info and record.exc_info[0] == ssl.SSLError)


class Module:
    """The HTTP server module"""
    runner: web.AppRunner
    site: web.TCPSite
    route_table_def: web.RouteTableDef
    main_app: web.Application

    """HTTPServer exposes HTTP endpoints for interaction from outside"""

    async def init(self):
        """Sets up an HTTPServer"""
        self.cfg = await self.core.cfg.register_domain(
            "http-server", self, schema=CONFIG_SCHEMA)

        if not self.core.start_args.verbose:
            logging.getLogger("asyncio").addFilter(SSLLogFilter())

        self.core.event_engine.register(
            EVENT_CORE_BOOTSTRAP_COMPLETE)(self.start)

    @web.middleware
    async def middleware(self, request: web.Request, handler) -> web.Response:
        """Workaround for tasks never being completed"""
        response = await handler(request)
        self.core.loop.call_soon(request.protocol.close)
        return response

    async def start(self, *args):
        """Start the HTTP server"""
        self.main_app = web.Application(middlewares=[self.middleware])
        self.route_table_def = web.RouteTableDef()

        await self.core.event_engine.gather(
            "http_add_main_routes",
            router=self.route_table_def)
        await self.core.event_engine.gather(
            "http_add_main_subapps",
            main_app=self.main_app)

        self.main_app.add_routes(self.route_table_def)
        self.runner = web.AppRunner(self.main_app)
        await self.runner.setup()

        if self.cfg["ssl"]:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.verify_mode = ssl.CERT_OPTIONAL
            context.load_cert_chain(
                self.cfg["ssl"]["certificate"],
                self.cfg["ssl"]["key"])
        else:
            context = None

        # Windows doesn't support reuse_port
        self.site = web.TCPSite(
            self.runner,
            self.cfg["host"],
            self.cfg["port"],
            reuse_address=True,
            reuse_port=os.name != "nt",
            ssl_context=context)
        await self.site.start()
        LOGGER.info("Started the HTTP server on %s:%s",
                    self.cfg["host"], self.cfg["port"])

    async def stop(self):
        """Stop the HTTP server"""
        LOGGER.info("Stopping the HTTP server on %s:%s",
                    self.cfg["host"], self.cfg["port"])
        try:
            await self.site.stop()
            await self.runner.cleanup()
        except AttributeError:
            return

    async def apply_new_configuration(self, domain, new_config) -> None:
        """Applies new configuration"""
        await self.stop()
        self.cfg = new_config
        await self.start()

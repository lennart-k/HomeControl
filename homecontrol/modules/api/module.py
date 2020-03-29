"""The API for HomeControl"""

import logging

from typing import Callable
import voluptuous as vol
from aiohttp import web

from .endpoints import add_routes

SPEC = {
    "name": "API"
}

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Required("headers", default={}): {vol.Coerce(str): vol.Coerce(str)}
})


class Module:
    """The API app module"""
    api_app: web.Application

    async def init(self):
        """Initialise the API app"""
        self.api_app = None

        # Prohibit reloading of the configuration
        self.cfg = await self.core.cfg.register_domain(
            "api-server", schema=CONFIG_SCHEMA)

        @self.core.event_engine.register("http_add_main_subapps")
        async def add_subapp(event, main_app):
            middlewares = self.middlewares()
            await self.core.event_engine.gather(
                "http_add_api_middlewares", middlewares=middlewares)
            self.api_app = web.Application(middlewares=middlewares)
            self.api_app["core"] = self.core
            self.api_app["module"] = self
            route_table = web.RouteTableDef()
            await self.core.event_engine.gather(
                "http_add_api_routes", router=route_table)
            self.api_app.add_routes(route_table)
            add_routes(self.api_app)
            main_app.add_subapp("/api", self.api_app)

    def middlewares(self) -> list:
        """Return middlewares"""
        middlewares = []

        @middlewares.append
        @web.middleware
        async def config_headers(
                request: web.Request, handler: Callable) -> web.Response:
            response = await handler(request)
            response.headers.update(self.cfg.get("headers", {}))
            return response

        return middlewares

    async def stop(self) -> None:
        """Stop the API app"""
        if self.api_app and self.api_app.frozen:
            await self.api_app.cleanup()

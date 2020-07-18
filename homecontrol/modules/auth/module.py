"""Provides OAuth2 for HomeControl"""
import logging
from typing import Callable

import voluptuous as vol
from aiohttp import web

from homecontrol.core import Core
from homecontrol.dependencies.entity_types import ModuleDef

from .auth import AuthManager
from .auth.auth_providers import AUTH_PROVIDERS
from .auth.login_flows import FlowManager
from .endpoints import add_routes

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Required("providers"): vol.Schema([
        vol.Schema({
            vol.Required("type"): str
        }, extra=vol.ALLOW_EXTRA)
    ]),
    vol.Required("login-flows", default={}): object
})


class Module(ModuleDef):
    """The authentication module"""
    core: Core
    auth_manager: AuthManager
    flow_manager: FlowManager

    async def init(self) -> None:
        """Initialises the module"""
        self.cfg = await self.core.cfg.register_domain(
            "auth", schema=CONFIG_SCHEMA)
        self.core.event_bus.register(
            "http_add_main_middlewares")(self.add_middlewares)
        self.core.event_bus.register(
            "http_add_api_middlewares")(self.add_middlewares)
        self.core.event_bus.register(
            "http_add_api_subapps")(self.add_subapp)

        self.auth_app = web.Application(
            middlewares=[self.check_authentication])
        self.auth_app["core"] = self.core
        self.auth_app["auth"] = self
        add_routes(self.auth_app)

        self.auth_manager = AuthManager(self.core)
        self.flow_manager = FlowManager(
            self.auth_manager, self.cfg["login-flows"])

        self.auth_providers = {
            cfg["type"]: AUTH_PROVIDERS[cfg["type"]](self.auth_manager, cfg)
            for cfg in self.cfg["providers"]
        }

    def _log_invalid_auth(self, request: web.Request) -> None:
        LOGGER.warning(
            "Unauthorized API request: %s %s from %s with %s",
            request.method, request.path, request.host,
            request.headers.get("User-Agent")
        )

    async def add_subapp(self, event, app: web.Application) -> None:
        """Adds the auth subapp to the api"""
        app.add_subapp("/auth", self.auth_app)

    async def add_middlewares(self, event, middlewares: list) -> None:
        """Adds the auth middleware to the API app"""
        middlewares.append(self.check_authentication)

    @web.middleware
    async def check_authentication(
            self, request: web.Request, handler: Callable) -> web.Response:
        """The middleware to check for authentication"""
        if getattr(handler, "allow_banned", False):
            return await handler(request)

        # pylint: disable=singleton-comparison
        for provider_name, provider in self.auth_providers.items():
            request["user"] = user = await provider.validate_request(
                request)
            if user is not None:
                break

        # user is False means access is forbidden
        if user is False:
            if handler.log_invalid:
                self._log_invalid_auth(request)
            raise web.HTTPUnauthorized(
                text="401: You are banned from using this endpoint")

        # Owner required but user is not owner
        if (getattr(handler, "owner_only", False)
                and not getattr(user, "owner", False)):
            if handler.log_invalid:
                self._log_invalid_auth(request)
            raise web.HTTPUnauthorized(
                text="401: You need owner permissions for this endpoint")

        # No user found
        if getattr(handler, "require_user", False) and not user:
            if handler.log_invalid:
                self._log_invalid_auth(request)
            raise web.HTTPUnauthorized(
                text="401: You need to log in for this endpoint")

        return await handler(request)

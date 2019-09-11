"""The API for HomeControl"""

import logging
from collections import ChainMap
# pylint: disable=no-name-in-module
from json import JSONDecodeError

import voluptuous as vol
from aiohttp import web

from homecontrol.dependencies import json
from homecontrol.dependencies.json_response import JSONResponse
from homecontrol.const import (
    ERROR_ITEM_NOT_FOUND,
    ITEM_STATE_NOT_FOUND,
    ITEM_ACTION_NOT_FOUND,
    ERROR_INVALID_ITEM_STATES,
    ERROR_INVALID_ITEM_STATE,
    ItemStatus
)
from homecontrol.exceptions import (
    ItemNotOnlineError
)

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Required("headers", default={}): {vol.Coerce(str): vol.Coerce(str)}
})
STATE_COMMIT_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)


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
            route_table = self.routes()
            await self.core.event_engine.gather(
                "http_add_api_routes", router=route_table)
            self.api_app.add_routes(route_table)
            main_app.add_subapp("/api", self.api_app)

    def middlewares(self) -> list:
        """Return middlewares"""
        middlewares = []

        @middlewares.append
        @web.middleware
        async def config_headers(request, handler):
            response = await handler(request)
            response.headers.update(self.cfg.get("headers", {}))
            return response

        return middlewares

    async def stop(self):
        """Stop the API app"""
        if self.api_app and self.api_app.frozen:
            await self.api_app.cleanup()

    def routes(self) -> web.RouteTableDef:
        """Return the API routes"""
        # pylint: disable=invalid-name,too-many-locals,too-many-statements
        r = web.RouteTableDef()

        @r.get("/ping")
        async def ping(request: web.Request) -> JSONResponse:
            """Handle /ping"""
            return JSONResponse("PONG")

        @r.post("/core/shutdown")
        async def shutdown(request: web.Request) -> JSONResponse:
            """Handle /core/shutdown"""
            self.core.loop.call_soon(self.core.shutdown)
            return JSONResponse("Shutting down")

        @r.post("/core/restart")
        async def restart(request: web.Request) -> JSONResponse:
            self.core.loop.call_soon(self.core.restart)
            return JSONResponse("Restarting")

        @r.post("/core/config/reload")
        async def reload_config(request: web.Request) -> JSONResponse:
            await self.core.cfg.reload_config()
            return JSONResponse("Reloaded configuration")

        @r.get("/items")
        async def get_items(request: web.Request) -> JSONResponse:
            return JSONResponse([
                {
                    "id": item.identifier,
                    "name": item.name,
                    "type": item.type,
                    "module": item.module,
                    "status": item.status,
                    "actions": list(item.actions.actions.keys()),
                    "states": await item.states.dump()
                } for item in self.core.item_manager.items.values()
            ])

        @r.get("/item/{id}")
        async def get_item(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.item_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            return JSONResponse({
                "id": item.identifier,
                "type": item.type,
                "module": item.module,
                "config": item.cfg,
                "status": item.status
            })

        @r.post("/item/{id}/reload")
        async def reload_item(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.item_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            await self.core.item_manager.recreate_item(item)

            return JSONResponse({
                "message": f"Item {identifier} recreated",
                "status": item.status
            })

        @r.get("/item/{id}/states")
        async def get_item_states(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.item_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            return JSONResponse({
                "item": item,
                "type": item.type,
                "states": await item.states.dump(),
            })

        @r.post("/item/{id}/states")
        async def set_item_states(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.item_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            try:
                content = (await request.content.read()).decode()
                commit = STATE_COMMIT_SCHEMA(
                    json.loads(content) if content else {})
            # pylint: disable=broad-except
            except Exception as e:
                return JSONResponse(error=e)

            if not commit.keys() & item.states.states.keys() == commit.keys():
                return JSONResponse(error={
                    "type": ERROR_INVALID_ITEM_STATES,
                    "message": f"The given states {set(commit.keys())} do not"
                               f"comply with accepted states "
                               f"{set(item.states.states.keys())}"
                })

            if not item.status == ItemStatus.ONLINE:
                return JSONResponse(
                    error=ItemNotOnlineError(
                        f"The item {item.identifier} is not online"))

            return JSONResponse(dict(ChainMap(
                *[await item.states.set(state, value)
                  for state, value in commit.items()])))

        @r.post("/item/{id}/states/{state_name}")
        async def set_item_state(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.item_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            state_name = request.match_info["state_name"]

            if state_name not in item.states.states.keys():
                return JSONResponse(error={
                    "type": ERROR_INVALID_ITEM_STATE,
                    "message": f"The given state '{state_name}' does not exist"
                })

            if not item.status == ItemStatus.ONLINE:
                return JSONResponse(
                    error=ItemNotOnlineError(
                        f"The item {item.identifier} is not online"))

            try:
                content = (await request.content.read()).decode()
                value = json.loads(content) if content else {}
                result = await item.states.set(state_name, value)
            # pylint: disable=broad-except
            except (Exception, vol.error.Error) as e:
                return JSONResponse(error=e)

            return JSONResponse(result)

        @r.get("/item/{id}/states/{state_name}")
        async def get_item_state(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            state_name = request.match_info["state_name"]
            item = self.core.item_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            if state_name not in item.states.states:
                return JSONResponse(error={
                    "type": ITEM_STATE_NOT_FOUND,
                    "message": f"Couldn't get state {state_name}"
                               f"from item {identifier}"
                })

            return JSONResponse({
                "item": item,
                "type": item.type,
                "states": {
                    state_name: await item.states.get(state_name)
                }
            })

        @r.get("/item/{id}/action")
        async def get_actions(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.item_manager.items.get(identifier)
            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            return JSONResponse(data=list(item.actions.actions.keys()))

        @r.post("/item/{id}/action/{action_name}")
        @r.get("/item/{id}/action/{action_name}")
        async def execute_action(request: web.Request) -> JSONResponse:
            """
            Executes an item's action and returns a boolean indicating the
            success of the action. Changed states or other events can be
            handled through the websocket endpoint /events
            """

            identifier = request.match_info["id"]
            action_name = request.match_info["action_name"]
            item = self.core.item_manager.items.get(identifier)
            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            try:
                content = (await request.content.read()).decode()
                kwargs = json.loads(content) if content else {}
            except JSONDecodeError as e:
                return JSONResponse(error=e)

            if action_name not in item.actions.actions:
                return JSONResponse(error={
                    "type": ITEM_ACTION_NOT_FOUND,
                    "message": f"Item {identifier} of type {item.type} "
                               f"does not have an action {action_name}"
                })

            try:
                return JSONResponse({
                    "item": item,
                    "action": action_name,
                    "result": await item.actions.execute(action_name, **kwargs)
                })
            # pylint: disable=broad-except
            except Exception as e:
                return JSONResponse(error=e)

        # @r.route("*", "/{path:.*}")
        # async def not_found(request: web.Request) -> JSONResponse:
        #     return JSONResponse(error={
        #         "type": "404",
        #         "message": (f"Could not find route "
        #                     f"{request.method} {request.path}")
        #     }, status_code=404)

        return r

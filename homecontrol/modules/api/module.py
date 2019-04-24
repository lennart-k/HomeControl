from collections import ChainMap
import voluptuous as vol
from dependencies import json
from json import JSONDecodeError
from aiohttp import web
from dependencies.json_response import JSONResponse
from const import (
    ERROR_ITEM_NOT_FOUND,
    ITEM_STATE_NOT_FOUND,
    ITEM_ACTION_NOT_FOUND,
    ERROR_INVALID_ITEM_STATES,
    ERROR_INVALID_ITEM_STATE,
    STATE_COMMIT_SCHEMA
)

class Module:
    api_app: web.Application

    async def init(self):
        @event("http_add_main_subapps")
        async def add_subapp(event, main_app):
            middlewares = self.middlewares()
            await self.core.event_engine.gather("http_add_api_middlewares", middlewares=middlewares)
            self.api_app = web.Application(middlewares=middlewares)
            route_table = self.routes()
            await self.core.event_engine.gather("http_add_api_routes", router=route_table)
            self.api_app.add_routes(route_table)
            main_app.add_subapp("/api", self.api_app)

    def middlewares(self) -> list:
        middlewares = []

        @middlewares.append
        @web.middleware
        async def config_headers(request, handler):
            response = await handler(request)
            response.headers.update(self.core.cfg.get(
                "api-server", {}).get("headers", {}))
            return response

        return middlewares

    async def stop(self):
        if self.api_app.frozen:
            await self.api_app.cleanup()

    def routes(self) -> web.RouteTableDef:
        r = web.RouteTableDef()

        @event("state_change")
        async def on_item_state_change(event, item, changes: dict):
            for ws in self.event_sockets:
                try:
                    await ws.send_json({
                        "type": "state_change",
                        "item": item,
                        "changes": changes
                    }, dumps=json.dumps)

                except Exception as e:
                    print(e.__traceback__)

        @r.get("/ping")
        async def ping(request: web.Request) -> JSONResponse:
            return JSONResponse("PONG")

        @r.post("/core/shutdown")
        async def shutdown(request: web.Request) -> JSONResponse:
            self.core.loop.create_task(self.core.shutdown())
            return JSONResponse("Shutting down")

        @r.post("/core/restart")
        async def restart(request: web.Request) -> JSONResponse:
            self.core.loop.create_task(self.core.restart())
            return JSONResponse("Restarting")

        @r.get("/items")
        async def get_items(request: web.Request) -> JSONResponse:
            return JSONResponse([
                {
                    "id": item.identifier,
                    "name": item.name,
                    "type": item.type,
                    "module": item.module,
                    "online": item.status,
                    "actions": list(item.actions.actions.keys()),
                    "state": await item.states.dump()
                } for item in self.core.entity_manager.items.values()
            ])

        @r.get("/item/{id}")
        async def get_item(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.entity_manager.items.get(identifier)

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
                "online": item.status
            })

        @r.get("/item/{id}/state")
        async def get_item_states(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.entity_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            return JSONResponse({
                "item": item,
                "type": item.type,
                "state": await item.states.dump(),
            })

        @r.post("/item/{id}/state")
        async def set_item_states(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.entity_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            try:
                content = (await request.content.read()).decode()
                commit = STATE_COMMIT_SCHEMA(
                    json.loads(content) if content else {})
            except Exception as e:
                return JSONResponse(error=e)

            if not commit.keys() & item.states.states.keys() == commit.keys():
                return JSONResponse(error={
                    "type": ERROR_INVALID_ITEM_STATES,
                    "message": f"The given states {set(commit.keys())} do not comply with accepted states {set(item.states.states.keys())}"
                })

            return JSONResponse(dict(ChainMap(*[await item.states.set(state, value) for state, value in commit.items()])))

        @r.post("/item/{id}/state/{state_name}")
        async def set_item_states(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.entity_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            state_name = request.match_info["state_name"]

            if not state_name in item.states.states.keys():
                return JSONResponse(error={
                    "type": ERROR_INVALID_ITEM_STATE,
                    "message": f"The given state '{state_name}' does not exist"
                })

            try:
                content = (await request.content.read()).decode()
                value = json.loads(content) if content else {}
                result = await item.states.set(state_name, value)
            except (Exception, vol.error.Error) as e:
                return JSONResponse(error=e)

            return JSONResponse(result)

        @r.get("/item/{id}/state/{state_name}")
        async def get_item_state(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            state_name = request.match_info["state_name"]
            item = self.core.entity_manager.items.get(identifier)

            if not item:
                return JSONResponse(error={
                    "type": ERROR_ITEM_NOT_FOUND,
                    "message": f"No item found with identifier {identifier}"
                }, status_code=404)

            if state_name not in item.states.states:
                return JSONResponse(error={
                    "type": ITEM_STATE_NOT_FOUND,
                    "message": f"Couldn't get state {state_name} from item {identifier}"
                })

            return JSONResponse({
                "item": item,
                "type": item.type,
                "state": {
                    state_name: await item.states.get(state_name)
                }
            })

        @r.get("/item/{id}/action")
        async def get_actions(request: web.Request) -> JSONResponse:
            identifier = request.match_info["id"]
            item = self.core.entity_manager.items.get(identifier)
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
            Executes an item's action and returns a boolean indicating the success of the action.
            Changed states or other events can be handled through the websocket endpoint /websocket
            """

            identifier = request.match_info["id"]
            action_name = request.match_info["action_name"]
            item = self.core.entity_manager.items.get(identifier)
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
                    "message": f"Item {identifier} of type {item.type} does not have an action {action_name}"
                })

            try:
                return JSONResponse({
                    "item": item,
                    "action": action_name,
                    "result": await item.actions.execute(action_name, **kwargs)
                })
            except Exception as e:
                return JSONResponse(error=e)

        # @r.route("*", "/{path:.*}")
        # async def not_found(request: web.Request) -> JSONResponse:
        #     return JSONResponse(error={
        #         "type": "404",
        #         "message": f"Could not find route {request.method} {request.path}"
        #     }, status_code=404)

        return r

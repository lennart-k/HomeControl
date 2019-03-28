import json
import asyncio
from aiohttp import web, WSMsgType
from aiohttp.web import middleware
from dependencies.entity_types import Item
from dependencies.data_types import type_set, types
from datetime import datetime
import os


class JSONEncoder(json.JSONEncoder):  # TODO Plan out custom types
    def default(self, o):
        if Item in o.__class__.__bases__:
            return {
                "!type": "Item",
                "id": o.identifier
            }
        elif o.__class__ == datetime:
            return {
                "!type": "datetime",
                "data": o.isoformat()
            }
        elif o.__class__ in type_set:
            return {
                "!type": o.__class__.__name__,
                "data": o.dump()
            }
        return super().default(o)


class JSONDecoder(json.JSONDecoder):
    def __init__(self, core, *args, **kwargs):
        self.core = core
        json.JSONDecoder.__init__(
            self, object_hook=self._object_hook, *args, **kwargs)

    def _object_hook(self, obj):
        if "!type" in obj:
            if obj["!type"] == "Item":
                return self.core.entity_manager.items.get(obj.get("id", ""), None)
            elif obj["!type"] in types:
                return types[obj["!type"]].from_data(obj["data"])

        return obj


class Module:
    auth_check: None

    """
    HTTPServer exposes HTTP endpoints for interaction from outside
    """

    async def init(self):
        """
        Sets up an HTTPServer
        """

        self.main_app = web.Application(loop=self.core.loop)
        self.middlewares = []
        self.add_middlewares()
        self.api_app = web.Application(
            loop=self.core.loop, middlewares=self.middlewares)

        self.event_sockets = set()

        event("core_bootstrap_complete")(self.start)

    async def start(self, *args):
        self.route_table_def = web.RouteTableDef()
        self.routes()
        await self.core.event_engine.gather("http_add_api_routes", router=self.route_table_def)
        await self.core.event_engine.gather("http_add_api_subapps", api_app=self.api_app)
        await self.core.event_engine.gather("http_add_main_subapps", main_app=self.main_app)

        self.api_app.add_routes(self.route_table_def)
        self.main_app.add_subapp("/api", self.api_app)
        self.handler = self.main_app.make_handler(loop=self.core.loop)

        # Windows doesn't support reuse_port
        self.future = self.core.loop.create_server(self.handler, self.core.cfg["api-server"]["host"],
                                                   self.core.cfg["api-server"]["port"],
                                                   reuse_address=True, reuse_port=os.name != "nt")
        # asyncio.ensure_future(self.future, loop=self.core.loop)
        asyncio.run_coroutine_threadsafe(self.future, loop=self.core.loop)

    def add_middlewares(self):
        @middleware
        async def auth_check(request, handler):
            response = await handler(request)
            for header, value in {"Allow": "GET, HEAD, PUT, PATCH, POST, DELETE, OPTIONS",
                                           "Access-Control-Request-Method": "GET, HEAD, PUT, PATCH, POST, DELETE, OPTIONS",
                                           "Access-Control-Allow-Origin": "*",
                                           "Access-Control-Allow-Headers": "X-PINGOTHER, Content-Type"}.items():
                response.headers[header] = value
            return response

        self.middlewares.append(auth_check)

    def routes(self):
        r = self.route_table_def

        @r.route("OPTIONS", "/{tail:.*}")
        async def get_options(request):
            return web.Response(headers={"Allow": "GET, HEAD, PUT, PATCH, POST, DELETE, OPTIONS",
                                         "Access-Control-Request-Method": "GET, HEAD, PUT, PATCH, POST, DELETE, OPTIONS",
                                         "Access-Control-Allow-Origin": "*",
                                         "Access-Control-Allow-Headers": "X-PINGOTHER, Content-Type"})

        @r.get("/item/{id}")
        async def get_item(request):
            """
            Get information about an existing item
            """
            item = self.core.entity_manager.items.get(request.match_info["id"])
            if item:
                return web.Response(body=json.dumps({
                    "id": item.identifier,
                    "module": item.module.name,
                    "config": item.cfg,
                    "success": True
                }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                    content_type="application/json",
                    status=200)
            else:
                return web.Response(body=json.dumps({
                    "message": "Item doesn't exist",
                    "success": False
                }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                    content_type="application/json",
                    status=402)

        @r.post("/item/{id}/action/{name}")
        @r.get("/item/{id}/action/{name}")
        async def execute_action(request):
            """
            Executes an item's action and returns a boolean indicating the success of the action.
            Changed states or other events can be handled through the websocket endpoint /events
            """
            item = self.core.entity_manager.items.get(request.match_info["id"])
            if item:
                content = (await request.content.read()).decode()
                kwargs = json.loads(content, cls=JSONDecoder,
                                    core=self.core) if content else {}

                result = await item.actions.execute(request.match_info["name"], **kwargs)
                return web.Response(body=json.dumps({
                    "id": item.identifier,
                    "success": result
                }, sort_keys=True, indent=4, cls=JSONEncoder))
            else:
                return web.Response(body=json.dumps({
                    "message": "Item doesn't exist",
                    "success": False
                }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                    content_type="application/json",
                    status=402)

        @r.get("/item/{id}/state")
        async def get_item_state(request):
            item = self.core.entity_manager.items.get(request.match_info["id"])
            if item:
                return web.Response(
                    body=json.dumps(await item.states.dump(), sort_keys=True, indent=4, cls=JSONEncoder))
            else:
                return web.Response(body=json.dumps({
                    "message": "Item doesn't exist",
                    "success": False
                }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                    content_type="application/json",
                    status=402)

        @r.get("/item/{id}/state/{state}")
        async def get_specific_item_state(request):
            item = self.core.entity_manager.items.get(request.match_info["id"])
            if item:
                if request.match_info["state"] in item.states.states:
                    return web.Response(
                        body=json.dumps({
                            "item": item,
                            "states": {
                                request.match_info["state"]: await item.states.get(request.match_info["state"])
                            }
                        }, sort_keys=True, indent=4, cls=JSONEncoder))
                else:
                    return web.Response(body=json.dumps({
                        "message": "State doesn't exist",
                        "success": False
                    }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                        content_type="application/json",
                        status=402)

            else:
                return web.Response(body=json.dumps({
                    "message": "Item doesn't exist",
                    "success": False
                }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                    content_type="application/json",
                    status=402)

        @r.post("/item/{id}/state")
        async def set_item_state(request: web.Request):  # TODO NEW Decoder
            """
            Endpoint to set an item's state
            Wrap the states to change into the body as JSON encoded data
            It will return every states that changed as a result
            """
            item = self.core.entity_manager.items.get(request.match_info["id"])
            if item:
                try:
                    data = json.loads((await request.content.read()).decode(), cls=JSONDecoder, core=self.core)
                    results = {}
                    for state, value in data.items():
                        results.update(await item.states.set(state, value))

                    return web.Response(body=json.dumps({
                        "id": item.identifier,
                        "results": results,
                        "success": True
                    }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                        content_type="application/json",
                        status=200)
                except json.decoder.JSONDecodeError:
                    return web.Response(body=json.dumps({
                        "message": "Invalid JSON payload",
                        "success": False,
                    }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                        content_type="application/json",
                        status=402)
            else:
                return web.Response(body=json.dumps({
                    "message": "Item doesn't exist",
                    "success": False
                }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                    content_type="application/json",
                    status=402)

        @r.post("/item/{id}/state/{state}")
        async def set_specific_item_state(request: web.Request):
            """
            Endpoint to set an item's state
            Wrap the states to change into the body as JSON encoded data
            It will return every states that changed as a result
            """
            item = self.core.entity_manager.items.get(request.match_info["id"])
            if item:
                content = (await request.content.read()).decode()
                try:
                    data = json.loads(content, cls=JSONDecoder, core=self.core)
                    result = await item.states.set(request.match_info["state"], data)
                    if result:
                        return web.Response(body=json.dumps({
                            "id": item.identifier,
                            "results": result,
                            "success": True
                        }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                            content_type="application/json",
                            status=200)
                    else:
                        return web.Response(body=json.dumps({
                            "message": "State doesn't exist",
                            "success": False,
                        }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                            content_type="application/json",
                            status=402)
                except json.decoder.JSONDecodeError:
                    return web.Response(body=json.dumps({
                        "message": "Invalid state value",
                        "success": False,
                    }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                        content_type="application/json",
                        status=402)
            else:
                return web.Response(body=json.dumps({
                    "message": "Item doesn't exist",
                    "success": False
                }, sort_keys=True, indent=4, cls=JSONEncoder).encode(),
                    content_type="application/json",
                    status=402)

        @r.post("/item/create")  # TODO Implementation
        async def create_item(request):
            raise NotImplementedError()

        @r.post("/item/{id}/remove")  # TODO Implementation
        async def remove_item(request):
            raise NotImplementedError()

        @r.post("/core/restart")
        async def restart_core(request):
            self.core.loop.create_task(self.core.restart())
            return web.Response(body=json.dumps({
                "success": True
            }))

        @r.post("/core/shutdown")
        async def shutdown_core(request):
            self.core.loop.create_task(self.core.shutdown())
            return web.Response(body=json.dumps({
                "success": True
            }))

        @r.get("/events")
        async def events_websocket(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            self.event_sockets.add(ws)

            async for msg in ws:
                if msg.type == WSMsgType.text:
                    if msg.data == 'close':
                        await ws.close()
                    else:
                        await ws.send_str(msg.data + '/answer')

            self.event_sockets.remove(ws)
            return ws

        @self.core.event_engine.register("state_change")
        async def on_state_change(event, item, changes):
            for ws in self.event_sockets:
                asyncio.ensure_future(
                    ws.send_str(json.dumps({"event_type": "state_change", "item": item.identifier, "changes": changes},
                                           cls=JSONEncoder)),
                    loop=self.core.loop)

        @self.core.event_engine.register("item_created")
        async def on_item_created(event, item):
            for ws in self.event_sockets:
                asyncio.ensure_future(
                    ws.send_str(json.dumps({"event_type": "item_created", "item": item},
                                           cls=JSONEncoder)),
                    loop=self.core.loop)

    async def stop(self):
        if self.main_app.frozen:
            await self.main_app.cleanup()
            self.future.close()

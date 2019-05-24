"""WebSocket module"""

import logging

from aiohttp import web

from homecontrol.dependencies import json

SPEC = """
meta:
    name: WebSocket API
"""

LOGGER = logging.getLogger(__name__)


class Module:
    """The WebSocket API"""

    async def init(self) -> None:
        """Initialise the WebSocket module"""
        self.event_sockets = set()
        # pylint: disable=undefined-variable
        event("state_change")(self.on_item_state_change)

        @event("http_add_api_routes")
        async def add_route(event, router):
            """Add an API route"""

            @router.get("/websocket")
            async def events_websockets(
                    request: web.Request) -> web.WebSocketResponse:
                """The WebSocket route"""
                websocket = web.WebSocketResponse()
                await websocket.prepare(request)
                self.event_sockets.add(websocket)

                async for msg in websocket:
                    if msg.data == "close":
                        await websocket.close()

                self.event_sockets.remove(websocket)
                return websocket

    async def on_item_state_change(self, event, item, changes: dict):
        """
        Pushes item state changes to all websocket subscribers
        """
        # pylint: disable=invalid-name
        for ws in self.event_sockets:
            try:
                await ws.send_json({
                    "type": "state_change",
                    "item": item,
                    "changes": changes
                }, dumps=json.dumps)

            # pylint: disable=broad-except
            except Exception:
                LOGGER.debug(
                    "An error occured when sending"
                    "a state update over WebSocket",
                    exc_info=True)

    async def stop(self):
        """Stop the WebSockets"""
        for websocket in list(self.event_sockets):
            await websocket.close()

"""WebSocket module"""

import asyncio
# pylint: disable=relative-beyond-top-level
import logging
from typing import TYPE_CHECKING, Union

from aiohttp import web

import voluptuous as vol
from homecontrol.const import MAX_PENDING_WS_MSGS
from homecontrol.dependencies.entity_types import ModuleDef

from .commands import WebSocketCommand, add_commands
from .message import WebSocketMessage

if TYPE_CHECKING:
    from homecontrol.modules.auth.module import AuthManager
    from homecontrol.modules.auth.auth.models import User
    from homecontrol.core import Core


SPEC = {
    "name": "WebSocket API",
    "description": "Provides events and state updates"
}

LOGGER = logging.getLogger(__name__)

MESSAGE_SCHEMA = vol.Schema({
    "type": str,
    vol.Optional("id"): str,
    vol.Optional("reply", default=True): bool
}, required=True, extra=vol.ALLOW_EXTRA)

EVENT_MESSAGE_SCHEMA = MESSAGE_SCHEMA.extend({"event": str})
RESPONSE_MESSAGE_SCHEMA = MESSAGE_SCHEMA.extend({"success": bool})


class Module(ModuleDef):
    """The WebSocket API"""

    async def init(self) -> None:
        """Initialise the WebSocket module"""
        self.sessions = set()
        self.command_handlers = {}
        self.core.event_engine.register(
            "http_add_api_routes")(self._add_api_route)
        self.core.event_engine.broadcast(
            "add_websocket_commands",
            add_command_handler=self.add_command_handler)

    async def _add_api_route(self, event, router):
        """Add an API route"""

        await self.core.event_engine.gather(
            "websocket_add_commands", add_command=self.add_command_handler)
        add_commands(self.add_command_handler)

        @router.get("/websocket")
        async def events_websockets(
                request: web.Request) -> web.WebSocketResponse:
            """The WebSocket route"""
            session = WebSocketSession(self.core, self, request)
            self.sessions.add(session)
            return await session.handle_connection()

    def add_command_handler(
            self, handler: WebSocketCommand) -> None:
        """
        Adds a command handler
        The handler must be decorated if no command parameter is given
        """
        schema = MESSAGE_SCHEMA.extend(
            handler.schema or {}).extend({"type": handler.command})
        handler.schema = schema
        self.command_handlers[handler.command] = handler

    async def stop(self) -> None:
        close_tasks = [session.close() for session in self.sessions]
        if not close_tasks:
            return
        await asyncio.wait(close_tasks, timeout=2)


class WebSocketSession:
    """
    A handler for WebSocket connections
    """
    websocket: web.WebSocketResponse
    writer_task: asyncio.Task
    handler_task: asyncio.Task
    user: "User"
    subscriptions: set

    def __init__(
            self, core: "Core", module: Module, request: web.Request) -> None:

        self.core = core
        self.module = module
        self.command_handlers = self.module.command_handlers
        self.request = request
        self.user = self.request["user"] or None
        self.writing_queue = asyncio.Queue(maxsize=MAX_PENDING_WS_MSGS)
        self.subscriptions = set()

    async def writer(self):
        """Write the messages from the queue"""
        while not self.websocket.closed:
            message: Union[str, dict] = await self.writing_queue.get()
            try:
                if isinstance(message, str):
                    await self.websocket.send_str(message)
                else:
                    await self.websocket.send_json(message)
            except (TypeError, ValueError):
                LOGGER.warning("Couldn't encode message: %s", message)

    def dispatch_message(self, message: WebSocketMessage) -> None:
        """Dispatches an incoming WS message"""
        command = message.type
        handler = self.command_handlers.get(command, None)

        async def _dispatch_message(handler: WebSocketCommand):
            try:
                result = await handler.handle()
                self.send_message(result)
            except Exception as error:  # pylint: disable=broad-except
                self.send_message(message.error(
                    type(error).__name__, str(error)))

        if not handler:
            return self.send_message(
                message.error("unknown_command", f"Command {command} unknown"))

        if not self.user and handler.use_auth:
            # Not authenticated
            return self.send_message(
                message.error("no_auth", "Please authenticate"))

        if handler.owner_only and not self.user.owner:
            return self.send_message(
                message.error(
                    "owner_only", "Only owners can access this command"))

        try:
            data = handler.schema(message.data)
        except vol.Invalid as e:
            return self.send_message(
                message.error("invalid_parameters", e.error_message))
        asyncio.run_coroutine_threadsafe(
            _dispatch_message(
                handler(message, self.core, self, data)),
            loop=self.core.loop)

    async def close(self):
        """Closes the connection"""
        self.writer_task.cancel()
        self.handler_task.cancel()
        await self.websocket.close()

    async def handle_connection(self) -> web.WebSocketResponse:
        """Establish a WebSocket connection"""
        self.websocket = web.WebSocketResponse(heartbeat=45)
        await self.websocket.prepare(self.request)
        LOGGER.debug("Connected to %s", self.request.host)
        self.writer_task = self.core.loop.create_task(self.writer())
        self.handler_task = asyncio.current_task()

        try:
            async for message in self.websocket:
                if message.type is not web.WSMsgType.TEXT:
                    LOGGER.debug("Non-text data received")
                    break
                try:
                    data = MESSAGE_SCHEMA(message.json())
                    self.dispatch_message(WebSocketMessage(data))
                except ValueError:
                    LOGGER.debug("Invalid JSON received")
                    break
                except vol.Invalid:
                    LOGGER.debug("Message doesn't match the schema")
                    break
        except asyncio.CancelledError:
            LOGGER.info("Connection closed by client")
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Unexpected error")
        finally:
            LOGGER.debug("Disconnected from %s", self.request.host)
            await self.close()

        return self.websocket

    def send_message(self, message: Union[str, dict]) -> None:
        """
        Sends a message
        message must be either of type str or JSON serialisable
        """
        try:
            self.writing_queue.put_nowait(message)
        except asyncio.QueueFull:
            self.core.loop.create_task(self.close())

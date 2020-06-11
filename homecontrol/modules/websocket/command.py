"""The WebSocket command class"""
import asyncio
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    # pylint: disable=relative-beyond-top-level
    from homecontrol.core import Core
    import voluptuous as vol
    from .message import WebSocketMessage
    from .module import WebSocketSession


class WebSocketCommand:
    """A WebSocket command handler"""
    command: str
    schema: "vol.Schema" = None
    core: "Core"
    message: "WebSocketMessage"
    session: "WebSocketSession"
    use_auth: bool = False
    owner_only: bool = False
    data: dict = None

    def __init__(self, message: "WebSocketMessage",
                 core: "Core", session: "WebSocketSession",
                 data: dict = None) -> None:
        self.message = message
        self.core = core
        self.session = session
        self.session.writer_task.add_done_callback(self._close)
        self.data = data

    async def handle(self):
        """Handle a command"""
        raise NotImplementedError()

    def _close(self, task: asyncio.Task):
        asyncio.run_coroutine_threadsafe(self.close(), loop=self.core.loop)

    async def close(self):
        """Triggered when websocket is closing"""

    def send_message(self, message: Union[dict, str]) -> None:
        """Sends a message"""
        self.session.send_message(message)

    def success(self, data) -> dict:
        """Return a success response"""
        return self.message.success(data)

    def error(self, error_type: str, message: str) -> dict:
        """Return a error"""
        return self.message.error(error_type, message)

    def error(
            self, error: Union[str, Exception], message: str = None) -> dict:
        """Return an error"""
        if isinstance(error, Exception):
            return self.message.error(type(error).__name__, str(error))
        return self.message.error(error, message)

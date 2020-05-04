"""The WebSocket command class"""
from typing import TYPE_CHECKING
import asyncio
if TYPE_CHECKING:
    # pylint: disable=relative-beyond-top-level
    from typing import Union
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

    def __init__(self, message: "WebSocketMessage",
                 core: "Core", session: "WebSocketSession") -> None:
        self.message = message
        self.core = core
        self.session = session
        self.session.writer_task.add_done_callback(self._close)

    async def handle(self):
        """Handle a command"""
        raise NotImplementedError()

    def _close(self, task: asyncio.Task):
        asyncio.run_coroutine_threadsafe(self.close(), loop=self.core.loop)

    async def close(self):
        """Triggered when websocket is closing"""

    def send_message(self, message: "Union[dict, str]") -> None:
        """Sends a message"""
        self.session.send_message(message)

    def success(self, data) -> dict:
        """Return a success response"""
        return self.message.success(data)

    def error(self, error_type: str, message: str) -> dict:
        """Return a error"""
        return self.message.error(error_type, message)

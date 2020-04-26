"""The WebSocket command class"""
from typing import TYPE_CHECKING
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

    def __init__(
            self, message: dict, core: "Core", session: "WebSocketSession"):
        self.message = message
        self.core = core
        self.session = session

    async def handle(self):
        """Handle a command"""
        raise NotImplementedError()

    def success(self, data) -> dict:
        """Return a success response"""
        return self.message.success(data)

    def error(self, error_type: str, message: str) -> dict:
        """Return a error"""
        return self.message.error(error_type, message)

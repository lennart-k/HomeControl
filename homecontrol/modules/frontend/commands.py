"""Frontend websocket commands"""
from typing import TYPE_CHECKING
from homecontrol.modules.websocket.command import WebSocketCommand
from homecontrol.modules.auth.decorator import needs_auth
if TYPE_CHECKING:
    from .module import Module


def add_commands(add_command):
    """Adds the websocket commands"""
    add_command(GetPanelsCommand)


@needs_auth()
class GetPanelsCommand(WebSocketCommand):
    """Returns the frontend panels"""
    command = "get_panels"

    async def handle(self) -> None:
        """Handle get_panels"""
        frontend: "Module" = self.core.modules.frontend
        return self.success([
            panel.to_dict() for panel in frontend.panels
        ])

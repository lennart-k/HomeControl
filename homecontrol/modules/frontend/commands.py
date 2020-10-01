"""Frontend websocket commands"""
from typing import TYPE_CHECKING, Any, Dict, Union, cast

from homecontrol.modules.auth.decorator import needs_auth
from homecontrol.modules.websocket.command import WebSocketCommand

if TYPE_CHECKING:
    from .module import Module


def add_commands(add_command):
    """Adds the websocket commands"""
    add_command(GetPanelsCommand)


@needs_auth()
class GetPanelsCommand(WebSocketCommand):
    """Returns the frontend panels"""
    command = "get_panels"

    async def handle(self) -> Union[str, Dict[Any, Any]]:
        """Handle get_panels"""
        frontend = cast("Module", self.core.modules.frontend)
        return self.success([
            panel.to_dict() for panel in frontend.panels
        ])

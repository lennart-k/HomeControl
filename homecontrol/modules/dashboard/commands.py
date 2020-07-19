"""Frontend websocket commands"""
from typing import TYPE_CHECKING, Any, Dict

from homecontrol.modules.auth.decorator import needs_auth
from homecontrol.modules.websocket.command import WebSocketCommand

if TYPE_CHECKING:
    from .module import Module


def add_commands(add_command):
    """Adds the websocket commands"""
    add_command(GetDashboardsCommand)


@needs_auth()
class GetDashboardsCommand(WebSocketCommand):
    """Returns the frontend panels"""
    command = "dashboard:get_dashboards"

    async def handle(self) -> Dict[Any, Any]:
        """Handle get_panels"""
        dashboard_mod: "Module" = self.core.modules.dashboard
        return self.success({
            "dashboards": {
                dashboard.identifier: {
                    "identifier": dashboard.identifier,
                    "name": dashboard.name,
                    "icon": dashboard.icon,
                    "sections": dashboard.sections,
                    "provider": dashboard.provider
                } for dashboard in dashboard_mod.dashboards.values()
            }
        })

"""The dashboard module"""
from typing import Any, Dict, List, cast

import voluptuous as vol
from attr import attrib, attrs

from homecontrol.const import EVENT_CORE_BOOTSTRAP_COMPLETE
from homecontrol.dependencies.entity_types import ModuleDef
from homecontrol.dependencies.linter_friendly_attrs import LinterFriendlyAttrs

from .commands import add_commands

SPEC = {
    "name": "Dashboard",
    "description": "Provides the Frontend's dashboards"
}

DASHBOARD_SCHEMA = vol.Schema({
    vol.Required("identifier"): str,
    vol.Required("sections", default=list): list,
    vol.Optional("name"): str,
    vol.Optional("icon"): str
}, extra=vol.ALLOW_EXTRA)

CONFIG_SCHEMA = vol.Schema([DASHBOARD_SCHEMA])


@attrs(slots=True)
class Dashboard(LinterFriendlyAttrs):
    """A dashboard"""
    identifier: str = attrib()
    provider: str = attrib()
    name: str = attrib(default=None)
    icon: str = attrib(default="")
    sections: list = attrib(default=[])

    def __attrs_post_init__(self) -> None:
        self.name = self.name or self.identifier


class Module(ModuleDef):
    """Provides dashboard configuration for frontend"""
    dashboards: Dict[str, Dashboard]

    async def init(self) -> None:
        self.dashboards = {}
        await self.load_yaml_config()

        @self.core.event_bus.register(EVENT_CORE_BOOTSTRAP_COMPLETE)
        async def add_websocket_commands(event) -> None:
            add_commands(self.core.modules.websocket.add_command_handler)

    async def load_yaml_config(self) -> None:
        """Loads YAML config"""
        cfg = cast(List[Dict[str, Any]], await self.core.cfg.register_domain(
            "dashboards",
            CONFIG_SCHEMA,
            default=[]
        ))
        for dashboard_config in cfg:
            dashboard = Dashboard(
                identifier=dashboard_config["identifier"],
                name=dashboard_config.get("name"),
                icon=dashboard_config.get("icon"),
                sections=dashboard_config["sections"],
                provider="yaml"
            )
            self.register_dashboard(dashboard)

    def register_dashboard(self, dashboard: Dashboard) -> None:
        """Registers a Dashboard"""
        self.dashboards[dashboard.identifier] = dashboard

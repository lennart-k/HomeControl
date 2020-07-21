"""The Frontend module"""

import json
import logging
import os
from typing import Optional, TYPE_CHECKING, Iterator, List

from aiohttp import web, web_urldispatcher
from yarl import URL

import voluptuous as vol
from homecontrol.const import EVENT_CORE_BOOTSTRAP_COMPLETE
from homecontrol.dependencies.entity_types import Module as ModuleType
from homecontrol.modules.api.view import APIView
from homecontrol_frontend import RESOURCE_PATH

from .commands import add_commands
from .panel import Panel

if TYPE_CHECKING:
    from homecontrol.core import Core


LOGGER = logging.getLogger(__name__)

PANEL_SCHEMA = vol.Schema({
    vol.Required("name"): str,
    vol.Required("route"): str,
    vol.Optional("icon", default=""): str,
    vol.Optional("iframe"): str
})

CONFIG_SCHEMA = vol.Schema({
    vol.Optional("resource-path", default=RESOURCE_PATH): str,
    vol.Optional("panels", default=[]): [PANEL_SCHEMA]
})
URL_BASE = "/frontend"


class AppView(web_urldispatcher.AbstractResource):
    """The /frontend view"""
    prefix: str
    core: "Core"
    resource_path: str
    index_path: str

    def __init__(self, module: "Module") -> None:
        super().__init__(name="frontend:index")
        self.module = module
        self.core = module.core
        self.resource_path = module.resource_path
        self.index_path = os.path.join(module.resource_path, "index.html")

    @property
    def _route(self):
        return web_urldispatcher.ResourceRoute("GET", self.get, self)

    @property
    def canonical(self) -> str:
        return "/"

    def url_for(self, **kwargs: str) -> URL:
        return URL("/")

    def __iter__(self) -> Iterator:
        return iter([self._route])

    def __len__(self) -> int:
        return 1

    async def resolve(self, request: web.Request):
        if request.url.parts[1] == "manifest.webmanifest":
            return None, {"GET"}
        return web_urldispatcher.UrlMappingMatchInfo({}, self._route), {"GET"}

    def add_prefix(self, prefix: str) -> None:
        """
        Add a prefix to processed URLs.
        Required for subapplications support.
        """
        self.prefix = prefix

    def get_info(self) -> dict:
        """Get information"""
        return {}

    def raw_match(self, path: str) -> bool:
        """Perform a raw match against path"""

    async def get(self, request: web.Request) -> Optional[web.FileResponse]:
        """GET /frontend/{path}"""
        path = request.path
        if path.startswith(self.prefix):
            path = path[len(self.prefix):]

        if path == "manifest.webmanifest":
            return
        resource = self.resource_path.rstrip("/") + path
        if not os.path.isfile(resource):
            resource = self.index_path
        return web.FileResponse(resource)


class ManifestView(APIView):
    """Serves the WebManifest"""
    path: str = "/manifest.webmanifest"

    async def get(self) -> web.Response:
        """GET /manifest.webmanifest"""
        module: "Module" = self.core.modules.frontend
        manifest = json.load(
            open(module.resource_path.rstrip("/") + self.path))

        data = json.dumps({
            **manifest,
            "name": "HomeControl",
            "short_name": "HomeControl",
            "start_url": "/frontend",
            "scope": "/frontend",
            "display": "standalone",
            "background_color": "#202327",
            "lang": "en-US"
        }, sort_keys=True)
        return web.Response(
            text=data, content_type="application/manifest+json")


class PanelsView(APIView):
    """Manages the panels"""
    path = "/panels"
    panels: List[Panel]
    module: "Module"

    def __init__(self, request):
        super().__init__(request)
        self.module = request.app["module"]
        self.panels = self.module.panels

    async def get(self) -> web.Response:
        """GET /panels"""
        return self.json([panel.to_dict() for panel in self.panels])


class Module(ModuleType):
    """The Frontend object"""
    frontend_app: web.Application
    panels: List[Panel]
    cfg: dict
    resource_path: str

    async def init(self):
        """Initialise the frontend app"""
        self.cfg = await self.core.cfg.register_domain(
            "frontend", schema=CONFIG_SCHEMA)
        self.panels = []
        self.load_yaml_panels()
        self.resource_path = self.cfg["resource-path"]
        self.frontend_app = web.Application()
        self.frontend_app["core"] = self.core
        self.frontend_app["module"] = self
        ManifestView.register_view(self.frontend_app)
        PanelsView.register_view(self.frontend_app)
        self.frontend_app.router.register_resource(AppView(self))

        @self.core.event_bus.register(EVENT_CORE_BOOTSTRAP_COMPLETE)
        async def add_websocket_commands(event) -> None:
            add_commands(self.core.modules.websocket.add_command_handler)

        @self.core.event_bus.register("http_add_main_routes")
        async def add_route(event, router: web.RouteTableDef) -> None:
            @router.get("/")
            async def get_index(request: web.Request) -> web.Response:
                return web.HTTPPermanentRedirect(URL_BASE)

        @self.core.event_bus.register("http_add_main_subapps")
        async def add_subapp(event, main_app: web.Application) -> None:
            main_app.add_subapp(URL_BASE, self.frontend_app)

    def register_panel(self, panel: Panel) -> None:
        """Register a panel"""
        self.panels.append(panel)

    def load_yaml_panels(self) -> None:
        """Loads panels from yaml configuration"""
        for entry in self.cfg["panels"]:
            self.panels.append(Panel(**entry))

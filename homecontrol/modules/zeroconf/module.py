"""zeroconf support for HomeControl"""

import asyncio
import logging
from functools import partial

from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

from homecontrol.const import (EVENT_CORE_BOOTSTRAP_COMPLETE,
                               EVENT_MODULE_LOADED)
from homecontrol.dependencies.entity_types import ModuleDef

LOGGER = logging.getLogger(__name__)


class Module(ModuleDef):
    """The zeroconf module"""
    async def init(self) -> None:
        """Initialise the zeroconf module"""
        self.registered_modules = set()
        self.zeroconf = Zeroconf()

        self.core.event_engine.register(
            EVENT_CORE_BOOTSTRAP_COMPLETE)(self.register_modules)
        self.core.event_engine.register(
            EVENT_MODULE_LOADED)(self.on_module_loaded)

    async def register_modules(self, event) -> None:
        """
        Registers all loaded modules when core bootstrap is complete
        """
        for module in self.core.modules:
            self.register_module(module)

    async def on_module_loaded(self, event, module: ModuleDef) -> None:
        """
        Handles a module that is loaded after core bootstrap.
        This is not intended but without this handler ModuleManager
        would have to be frozen after core bootstrap
        """
        await self.core.loop.run_in_executor(
            None, partial(self.register_module, module))

    def register_module(self, module: ModuleDef) -> None:
        """
        Checks if a module wants zeroconf discovery or if it already has
        a ServiceBrowser.
        If not, a ServiceBrowser is created
        """
        zeroconf_conf = module.spec.get("zeroconf")
        if not zeroconf_conf or module in self.registered_modules:
            return
        self.registered_modules.add(module)
        for service in zeroconf_conf:
            ServiceBrowser(self.zeroconf, service, handlers=[
                partial(self.dispatch_service, module=module)
            ])

    def dispatch_service(
            self, zeroconf: Zeroconf, service_type: str, name: str,
            state_change: ServiceStateChange, module: ModuleDef) -> None:
        """Dispatches a zeroconf service to a module"""
        LOGGER.debug(
            "Zeroconf service for %s: type=%s name=%s state=%s",
            module.name, service_type, name, state_change)
        asyncio.run_coroutine_threadsafe(module.handle_zeroconf(
            zeroconf=zeroconf,
            name=name,
            state_change=state_change
        ), loop=self.core.loop)

    async def stop(self) -> None:
        """Stop the zeroconf module"""
        self.zeroconf.close()

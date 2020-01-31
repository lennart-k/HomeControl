"""Custom python scripts in HomeControl"""

import os
import logging
import importlib

import voluptuous as vol
from homecontrol.const import EVENT_CORE_BOOTSTRAP_COMPLETE

SPEC = {
    "name": "Custom Scripts",
    "description": "Allows you to create custom scripts"
}

CONFIG_SCHEMA = vol.Schema({
    vol.Required("scripts", default=[]): [str]
})

LOGGER = logging.getLogger(__name__)


class Module:
    """Executes custom scripts"""
    async def init(self) -> None:
        """Inits the module"""
        self.cfg = await self.core.cfg.register_domain(
            "custom-scripts",
            handler=self,
            schema=CONFIG_SCHEMA,
            allow_reload=False
        )
        self.core.event_engine.register(EVENT_CORE_BOOTSTRAP_COMPLETE)(
            self.execute_scripts)

    async def execute_scripts(self, event) -> None:
        """Executes all configured scripts"""
        for script in self.cfg["scripts"]:
            await self.execute_script(script)

    async def execute_script(self, path: str) -> None:
        """
        Executes a script
        Note that this method does not contain any safety measures
        so watch out what scripts you run
        """
        LOGGER.info("Executing script at path '%s'", path)

        name = os.path.splitext(os.path.basename(path))[0]

        try:
            spec = importlib.util.spec_from_file_location(
                f"scripts.{name}", path)
            mod = importlib.util.module_from_spec(spec)
            mod.__dict__.update({
                "core": self.core,
                "loop": self.core.loop,
                "logger": logging.getLogger(f"scripts.{name}")
            })
            spec.loader.exec_module(mod)

        except Exception:  # pylint: disable=broad-except
            LOGGER.error(
                "An error occured when executing the script %s", path,
                exc_info=True)

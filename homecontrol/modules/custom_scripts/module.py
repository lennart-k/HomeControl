"""Custom python scripts in HomeControl"""

import os
import logging

import voluptuous as vol
from homecontrol.dependencies.validators import ConsistsOf

CONFIG_SCHEMA = vol.Schema({
    vol.Required("scripts", default=[]): ConsistsOf(str)
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
        event("core_bootstrap_complete")(self.execute_scripts)

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

        code = compile(
            open(path, "rb").read(),
            filename=path,
            mode="exec"
        )
        name = os.path.splitext(os.path.basename(path))[0]

        try:
            await self.core.loop.run_in_executor(
                None,
                lambda: exec(  # pylint: disable=exec-used
                    code, {},
                    {
                        "core": self.core,
                        "loop": self.core.loop,
                        "logger": logging.getLogger(f"scripts.{name}")
                    }
                )
            )
        except:  # pylint: disable=bare-except
            LOGGER.error(
                "An error occured when executing the script %s", path,
                exc_info=True)

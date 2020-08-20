"""ping module"""
import asyncio
import logging
import re
import sys
from asyncio.subprocess import PIPE, create_subprocess_shell
from contextlib import suppress

import voluptuous as vol

from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef

LOGGER = logging.getLogger(__name__)

SPEC = {
    "name": "ping"
}

if sys.platform == "win32":
    PING_COMMAND = "ping -n {count} -w 1000 {address}"
    PING_PATTERN = re.compile(
        r"(?P<min_ping>\d+)ms.+(?P<max_ping>\d+)ms.+(?P<average>\d+)ms")
else:
    PING_COMMAND = "ping -n -q -c {count} -W1 {address}"
    PING_PATTERN = re.compile(
        r"min\/avg\/max(\/mdev)? = "
        r"(?P<min_ping>\d+.\d+)\/(?P<average>\d+.\d+)"
        r"\/(?P<max_ping>\d+.\d+)(\/(\d+.\d+))? ms")


class PingSensor(Item):
    """An item that pings an address"""

    update_task: asyncio.Task
    online = StateDef()
    min_ping = StateDef()
    max_ping = StateDef()
    average = StateDef()
    config_schema = vol.Schema({
        "address": str,
        vol.Required("count", default=3): int,
        vol.Required("update_interval", default=60): int
    }, extra=vol.ALLOW_EXTRA)

    async def init(self) -> None:
        """Initialise the item"""
        self.update_task = self.core.loop.create_task(self.update_interval())
        self.command = PING_COMMAND.format(**self.cfg)

    async def update_interval(self) -> None:
        """Updates the states"""
        while True:
            await self.update()
            await asyncio.sleep(self.cfg["update_interval"])

    async def stop(self) -> None:
        self.update_task.cancel()

    @action("update")
    async def update(self) -> None:
        """Runs a ping"""
        ping_process = await create_subprocess_shell(
            self.command,
            stdin=None,
            stdout=PIPE,
            stderr=PIPE
        )
        try:
            out, err = await asyncio.wait_for(
                ping_process.communicate(), 4 * self.cfg["count"])

            if ping_process.returncode or err:
                self.states.update("online", False)
                LOGGER.error("Ping command returned an error: %s, '%s'\n%s",
                             ping_process.returncode, self.command, err)

            match = PING_PATTERN.search(str(out).split("\n")[-1])
            self.states.bulk_update(**match.groupdict(), online=True)

        except asyncio.TimeoutError:
            LOGGER.error("Ping command timed out")
            with suppress(Exception):
                ping_process.kill()
            self.states.update("online", False)

        except AttributeError:
            self.states.update("online", False)

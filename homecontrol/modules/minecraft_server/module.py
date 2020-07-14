"""A module for minecraft server status information"""
import asyncio
import logging

from mcstatus import MinecraftServer as MCServer

import voluptuous as vol
from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item, ItemStatus
from homecontrol.dependencies.state_proxy import StateDef

LOGGER = logging.getLogger(__name__)


class MinecraftServer(Item):
    """A Minecraft server item"""
    server: MCServer
    status_task: asyncio.Task = None
    config_schema = vol.Schema({
        vol.Required("host"): str,
        vol.Required("port", default=25565): int,
        vol.Required("ping-interval", default=30): int
    })

    players = StateDef(default=[])
    n_players = StateDef(default=0)
    max_players = StateDef()
    version = StateDef()
    description = StateDef()
    latency = StateDef()

    async def init(self) -> None:
        self.server = MCServer(self.cfg["host"], self.cfg["port"])
        self.status_task = self.core.loop.create_task(self._iter_status())

    async def _iter_status(self) -> None:
        while True:
            await self.get_status()
            await asyncio.sleep(self.cfg["ping-interval"])

    async def stop(self) -> None:
        if self.status_task:
            self.status_task.cancel()

    @action
    async def get_status(self) -> None:
        """Fetches the server's status"""
        try:
            status = await self.core.loop.run_in_executor(
                None, self.server.status)
        except OSError:
            self.update_status(ItemStatus.OFFLINE)
            return False
        except BaseException:  # pylint: disable=bare-except
            LOGGER.error("Error:", exc_info=True)
            return False

        self.update_status(ItemStatus.ONLINE)

        player_names = (
            [player.name for player in status.players.sample]
            if status.players.online else [])

        self.states.bulk_update(
            players=player_names,
            n_players=status.players.online,
            max_players=status.players.max,
            version=status.version.name,
            description=status.description.get("text"),
            latency=status.latency)

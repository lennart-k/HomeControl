"Chromecast module"
from contextlib import suppress
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, cast
from uuid import UUID

import pychromecast
import voluptuous as vol
from pychromecast.dial import DeviceStatus

from homecontrol.const import ItemStatus
from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item, ItemProvider, ModuleDef
from homecontrol.dependencies.state_proxy import StateDef
from homecontrol.dependencies.storage import Storage
from homecontrol.modules.media_player.module import MediaPlayer

if TYPE_CHECKING:
    from homecontrol.dependencies.item_manager import StorageEntry
    from zeroconf import Zeroconf
    from zeroconf import ServiceStateChange

LOGGER = logging.getLogger(__name__)


class Module(ModuleDef, ItemProvider):
    """The Chromecast module"""
    async def handle_zeroconf(
            self, zeroconf: "Zeroconf", name: str,
            state_change: "ServiceStateChange") -> None:
        """Handles Zeroconf"""
        # pylint: disable=import-outside-toplevel
        from zeroconf import ServiceStateChange
        if state_change is not ServiceStateChange.Added:
            return

        info = zeroconf.get_service_info("_googlecast._tcp.local.", name)
        host = ".".join([str(byte) for byte in info.addresses[0]])
        friendly_name = info.properties[b"fn"].decode()
        uuid = info.properties[b"id"].decode()
        identifier = ("chromecast_" + friendly_name.lower().replace(" ", "_")
                      + "_" + uuid[:4])

        await self.core.item_manager.register_entry(StorageEntry(
            type="chromecast.Chromecast",
            cfg={"host": host, "port": info.port},
            unique_identifier=uuid,
            name=friendly_name,
            identifier=identifier
        ))


class Chromecast(MediaPlayer):
    """The Chromecast item"""
    config_schema = vol.Schema({
        vol.Required("host"): vol.Coerce(str),
        vol.Required("port", default=8009): vol.Coerce(int)
    }, extra=vol.ALLOW_EXTRA)

    _chromecast: Optional[pychromecast.Chromecast] = None
    media_status = None
    device: Optional[DeviceStatus]

    position = StateDef(poll_interval=1, log_state=False)

    async def init(self) -> Optional[bool]:
        """Initialises the Chromecast item"""
        self.storage = Storage(
            self.core, f"item_data/{self.unique_identifier}", 1,
            storage_init=lambda: None,
            loader=lambda data: data and DeviceStatus(
                **{**data, "uuid": UUID(data["uuid"])}),
            dumper=lambda data: {**data._asdict(), "uuid": data.uuid.hex})

        self.device = pychromecast.get_device_status(
            self.cfg["host"]) or self.storage.load_data()
        if not self.device:
            LOGGER.error(
                "Could not connect to chromecast at %s:%s",
                self.cfg["host"], self.cfg["port"])
            return

        self.storage.schedule_save(self.device)

        def _connect():
            chromecast = pychromecast.Chromecast(
                host=self.cfg["host"], port=self.cfg["port"],
                device=self.device)

            chromecast.media_controller.register_status_listener(self)
            chromecast.register_connection_listener(self)
            chromecast.start()

            self._chromecast = chromecast

        self.core.loop.run_in_executor(None, _connect)
        return False

    @position.getter()
    async def get_position(self) -> Optional[float]:
        """Position getter"""
        if not self.media_status:
            return None
        position = self.media_status.current_time
        if self.media_status.player_state == "PLAYING":
            position += (datetime.utcnow()
                         - self.media_status.last_updated).seconds
        return position

    @position.setter()
    async def set_position(self, position: int) -> Dict[str, Any]:
        value = max(
            0, min(position, cast(int, await self.states.get("duration"))))
        self._chromecast.media_controller.seek(value)
        return {"position": value}

    @action("pause")
    async def action_pause(self) -> None:
        self._chromecast.media_controller.pause()

    async def set_playing(self, playing: bool) -> Dict[str, Any]:
        if playing:
            self._chromecast.media_controller.play()
        else:
            self._chromecast.media_controller.pause()
        return {"playing": playing}

    async def set_volume(self, volume: int) -> Dict[str, Any]:
        self._chromecast.set_volume(volume / 100)
        return {"volume": volume}

    @action("play")
    async def action_play(self) -> None:
        """Action: Play"""
        self._chromecast.media_controller.play()

    @action("play_url")
    async def action_play_url(self, url: str, mime: str) -> None:
        """Action: Play URL"""
        self._chromecast.media_controller.play_media(
            url=url, content_type=mime)

    @action("previous")
    async def action_previous(self) -> None:
        """Action: Previous"""
        self._chromecast.media_controller.rewind()

    @action("next")
    async def action_next(self) -> None:
        """Action: Next"""
        self._chromecast.media_controller.skip()

    @action("stop")
    async def action_stop(self) -> None:
        """Action: stop"""
        if self._chromecast.media_controller.is_active:
            self._chromecast.media_controller.stop()

    @action("quit")
    async def action_quit(self) -> None:
        """Action: Quit casting"""
        self._chromecast.quit_app()

    def new_media_status(self, status) -> None:
        """Handle new media status"""
        self.core.loop.run_in_executor(None, self.update_media_status, status)

    def new_connection_status(self, status) -> None:
        """Handles connection status updates"""
        if status.status == 'CONNECTED':
            self.update_status(ItemStatus.ONLINE)
        else:
            self.update_status(ItemStatus.OFFLINE)

    def update_media_status(self, status) -> None:
        """Update media status"""
        self.media_status = status
        self.states.bulk_update(
            position=status.current_time,
            playing=status.player_state == "PLAYING",
            content_type=status.content_type,
            volume=int(status.volume_level * 100),
            duration=status.duration,
            title=status.title,
            artist=status.artist,
            album=status.album_name,
            cover=status.images[0].url if status.images else None
        )

    async def stop(self) -> None:
        if not self._chromecast:
            return
        with suppress(Exception):
            self._chromecast.disconnect(1)

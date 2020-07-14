"Chromecast module"

import time
from contextlib import suppress
from typing import TYPE_CHECKING

import pychromecast

import voluptuous as vol
from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item, ModuleDef
from homecontrol.dependencies.item_manager import StorageEntry
from homecontrol.dependencies.state_proxy import StateDef

if TYPE_CHECKING:
    from zeroconf import Zeroconf

with suppress(ImportError):
    from zeroconf import ServiceStateChange


class Module(ModuleDef):
    """The Chromecast module"""
    async def handle_zeroconf(
            self, zeroconf: "Zeroconf", name: str,
            state_change: "ServiceStateChange") -> None:
        """Handles Zeroconf"""
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
            identifier=identifier,
            provider="chromecast"
        ))


class Chromecast(Item):
    """The Chromecast item"""
    config_schema = vol.Schema({
        vol.Required("host"): vol.Coerce(str),
        vol.Required("port", default=8009): vol.Coerce(int)
    }, extra=vol.ALLOW_EXTRA)

    last_time_jump = 0
    last_status = 0
    playing = StateDef(default=False)
    metadata = StateDef(default_factory=lambda: {})
    duration = StateDef(default=0)
    playtime = StateDef(default=0, poll_interval=1, log_state=False)
    content_type = StateDef()
    muted = StateDef(default=False)
    volume = StateDef(default=0)

    async def init(self) -> None:
        """Initialises the Chromecast item"""
        try:
            self.chromecast = pychromecast.Chromecast(
                host=self.cfg["host"], port=self.cfg["port"])
        except pychromecast.error.ChromecastConnectionError:
            return False

        self.media_controller = self.chromecast.media_controller
        self.last_time_jump = vars(
            self.media_controller).get("current_time", 0)
        self.states.bulk_update(
            playing=vars(
                self.media_controller).get("player_state") == "PLAYING",
            content_type=self.media_controller.status.content_type,
            metadata=self.media_controller.status.media_metadata,
            volume=int(self.media_controller.status.volume_level * 100),
        )
        self.media_controller.register_status_listener(self)

    @playtime.getter()
    async def get_playtime(self) -> float:
        """Getter for playtime"""
        return (self.media_controller.status.current_time
                + (time.time() - self.last_status
                   if await self.states.get('playing') else 0))

    @playtime.setter()
    async def set_playtime(self, value: float) -> dict:
        """"Setter for playtime"""
        value = max(0, min(value, await self.states.get("duration")))
        self.media_controller.seek(value)
        return {"playtime": value}

    @action("pause")
    async def action_pause(self) -> bool:
        """Action: Pause"""
        self.media_controller.pause()
        return True

    @playing.setter()
    async def set_playing(self, value) -> dict:
        """Setter for playing"""
        if value:
            self.media_controller.play()
        else:
            self.media_controller.pause()
        return {"playing": value}

    @action("play")
    async def action_play(self) -> bool:
        """Action: Play"""
        self.media_controller.play()
        return True

    @action("play_url")
    async def action_play_url(self, url: str, mime: str) -> None:
        """Action: Play URL"""
        self.media_controller.play_media(url=url, content_type=mime)

    @action("rewind")
    async def action_rewind(self) -> None:
        """Action: Rewind"""
        self.media_controller.rewind()

    @action("skip")
    async def action_skip(self) -> None:
        """Action: Skip"""
        self.media_controller.skip()

    @action("stop")
    async def action_stop(self) -> None:
        """Action: stop"""
        if self.media_controller.is_active:
            self.media_controller.stop()

    @volume.setter()
    async def set_volume(self, value: int) -> dict:
        """Setter for volume"""
        self.chromecast.set_volume(value / 100)
        return {"volume": value}

    @muted.setter()
    async def set_muted(self, value: bool) -> dict:
        """Setter for muted"""
        self.chromecast.set_volume_muted(bool(value))
        return {"muted": value}

    @action("toggle_muted")
    async def action_toggle_muted(self) -> None:
        """Action: Toggle muted"""
        new_state = not await self.states.get("muted")
        await self.states.set("muted", new_state)

    @action("quit")
    async def action_quit(self) -> None:
        """Action: Quit casting"""
        self.chromecast.quit_app()

    def new_cast_status(self, status) -> None:
        """Handle new cast status"""
        self.core.event_engine.broadcast(
            "chromecast_cast_status", status=status)

    def new_media_status(self, status) -> None:
        """Handle new media status"""
        self.core.loop.create_task(self.update_media_status(status))

    async def update_media_status(self, status) -> None:
        """Update media status"""
        self.last_time_jump = status.current_time
        self.last_status = time.time()

        self.states.bulk_update(
            playtime=status.current_time,
            playing=vars(status).get("player_state") == "PLAYING",
            content_type=status.content_type,
            metadata=status.media_metadata,
            volume=int(status.volume_level * 100),
            duration=status.duration,
        )

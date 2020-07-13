"""Module for Yamaha AV receivers"""
import asyncio
import logging

import rxv
from requests.exceptions import ConnectionError

import voluptuous as vol
from homecontrol.dependencies.action_engine import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef

# pylint: disable=redefined-builtin


logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("rxv").setLevel(logging.CRITICAL)

CTRL_URL = "http://{host}/YamahaRemoteControl/ctrl"


class YamahaAVReceiver(Item):
    """The YamahaAVReceiver item"""
    update_task = asyncio.Task
    config_schema = vol.Schema({
        vol.Required("host"): str
    }, extra=vol.ALLOW_EXTRA)

    input_source = StateDef()
    volume = StateDef()
    muted = StateDef()
    available_inputs = StateDef(default=[])
    playback_status = StateDef()
    artist = StateDef()
    title = StateDef()
    album = StateDef()
    on = StateDef(default=False)

    async def init(self):
        """Initialise the item"""
        self.play_status = None
        try:
            self.av_receiver = rxv.RXV(CTRL_URL.format(host=self.cfg["host"]))
        except (ConnectionError, ConnectionRefusedError):
            return False

        self.update_task = self.core.loop.create_task(self.interval_update())

    @on.setter(vol.Schema(bool))
    async def set_on(self, value: bool) -> dict:
        """Setter for on"""
        self.av_receiver.on = value
        return {"on": value}

    @on.getter()
    async def get_on(self) -> bool:
        """Getter for on"""
        return self.av_receiver.on

    @input_source.setter(vol.Schema(str))
    async def set_input(self, value: str) -> dict:
        """Setter for input"""
        self.av_receiver.input = value
        return {"input": value}

    @input_source.getter()
    async def get_input(self) -> str:
        """Getter for input"""
        return self.av_receiver.input

    @volume.setter(vol.Coerce(float))
    async def set_volume(self, value: float) -> dict:
        """Setter for volume"""
        self.av_receiver.volume = value
        return {"volume": value}

    @volume.getter()
    async def get_volume(self) -> float:
        """Getter for volume"""
        return self.av_receiver.volume

    @muted.setter(vol.Schema(bool))
    async def set_muted(self, value: bool) -> dict:
        """Setter for muted"""
        self.av_receiver.mute = value
        return {"muted": value}

    @muted.getter()
    async def get_muted(self) -> bool:
        """Getter for muted"""
        return self.av_receiver.mute

    @artist.getter()
    async def get_artist(self):
        """Getter for artist"""
        if self.play_status:
            return self.play_status.artist

    @album.getter()
    async def get_album(self):
        """Getter for album"""
        if self.play_status:
            return self.play_status.album

    @title.getter()
    async def get_title(self):
        """Getter for title"""
        if self.play_status:
            return self.play_status.song

    @action("play")
    async def action_play(self):
        """Action play"""
        self.av_receiver.play()

    @action("pause")
    async def action_pause(self):
        """Action pause"""
        self.av_receiver.pause()

    @action("stop")
    async def action_stop(self):
        """Action stop"""
        self.av_receiver.stop()

    @action("skip")
    async def action_skip(self):
        """Action skip"""
        self.av_receiver.next()

    @action("rewind")
    async def action_rewind(self):
        """Action rewind"""
        self.av_receiver.previous()

    @action("toggle_muted")
    async def action_toggle_muted(self):
        """Action toggle mute"""
        self.av_receiver.mute = not self.av_receiver.mute

    async def get_playback_status(self) -> bool:
        """Getter for playback status"""
        return self.av_receiver.is_playback_supported()

    async def interval_update(self):
        """Triggers the update every 2 seconds"""
        while True:
            await self.update()
            await asyncio.sleep(2)

    async def update(self):
        """Updates play_status and inputs"""
        try:
            self.play_status = self.av_receiver.play_status()
        except Exception:  # pylint: disable=broad-except
            self.play_status = None

        available_inputs = {
            raw_name or name
            for name, raw_name
            in self.av_receiver.inputs().get("available_inputs").items()}
        self.states.update("available_inputs", available_inputs)

    async def stop(self) -> None:
        """Stop the item"""
        self.update_task.cancel()

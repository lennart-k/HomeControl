"""Module for Yamaha AV receivers"""

import logging

import rxv
# pylint: disable=redefined-builtin
from requests.exceptions import ConnectionError

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("rxv").setLevel(logging.CRITICAL)

CTRL_URL = "http://{host}/YamahaRemoteControl/ctrl"


class YamahaAVReceiver:
    """The YamahaAVReceiver item"""
    async def init(self):
        """Initialise the item"""
        self.play_status = None
        try:
            self.av_receiver = rxv.RXV(CTRL_URL.format(host=self.cfg["host"]))
        except (ConnectionError, ConnectionRefusedError):
            return False

        self.core.tick_engine.tick(2)(self.update)

    async def set_on(self, value: bool) -> dict:
        """Setter for on"""
        self.av_receiver.on = value
        return {"on": value}

    async def get_on(self) -> bool:
        """Getter for on"""
        return self.av_receiver.on

    async def set_input(self, value: str) -> dict:
        """Setter for input"""
        self.av_receiver.input = value
        return {"input": value}

    async def get_input(self) -> str:
        """Getter for input"""
        return self.av_receiver.input

    async def set_volume(self, value: float) -> dict:
        """Setter for volume"""
        self.av_receiver.volume = value
        return {"volume": value}

    async def get_volume(self) -> float:
        """Getter for volume"""
        return self.av_receiver.volume

    async def set_muted(self, value: bool) -> dict:
        """Setter for muted"""
        self.av_receiver.mute = value
        return {"muted": value}

    async def get_muted(self) -> bool:
        """Getter for muted"""
        return self.av_receiver.mute

    async def action_play(self):
        """Action play"""
        self.av_receiver.play()

    async def action_pause(self):
        """Action pause"""
        self.av_receiver.pause()

    async def action_stop(self):
        """Action stop"""
        self.av_receiver.stop()

    async def action_skip(self):
        """Action skip"""
        self.av_receiver.next()

    async def action_rewind(self):
        """Action rewind"""
        self.av_receiver.previous()

    async def action_toggle_muted(self):
        """Action toggle mute"""
        self.av_receiver.mute = not self.av_receiver.mute

    async def get_playback_status(self) -> bool:
        """Getter for playback status"""
        return self.av_receiver.is_playback_supported()

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
        await self.states.update("available_inputs", available_inputs)

    async def get_artist(self):
        """Getter for artist"""
        if self.play_status:
            return self.play_status.artist

    async def get_album(self):
        """Getter for album"""
        if self.play_status:
            return self.play_status.album

    async def get_title(self):
        """Getter for title"""
        if self.play_status:
            return self.play_status.song

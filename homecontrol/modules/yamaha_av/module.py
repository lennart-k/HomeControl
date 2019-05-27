from requests.exceptions import ConnectionError
import rxv
import logging

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("rxv").setLevel(logging.CRITICAL)

CTRL_URL = "http://{host}/YamahaRemoteControl/ctrl"


class YamahaAVReceiver:
    async def init(self):
        self.play_status = None
        try:
            self.rx = rxv.RXV(CTRL_URL.format(host=self.cfg["host"]))
        except (ConnectionError, ConnectionRefusedError):
            return False

        tick(2)(self.update)

    async def set_on(self, value: bool) -> dict:
        self.rx.on = value
        return {"on": value}

    async def get_on(self) -> bool:
        return self.rx.on

    async def set_input(self, value: str) -> dict:
        self.rx.input = value
        return {"input": value}

    async def get_input(self) -> str:
        return self.rx.input

    async def set_volume(self, value: float) -> dict:
        self.rx.volume = value
        return {"volume": value}

    async def get_volume(self) -> float:
        return self.rx.volume

    async def set_muted(self, value: bool) -> dict:
        self.rx.mute = value
        return {"muted": value}

    async def get_muted(self) -> bool:
        return self.rx.mute

    async def action_play(self):
        self.rx.play()

    async def action_pause(self):
        self.rx.pause()

    async def action_stop(self):
        self.rx.stop()

    async def action_skip(self):
        self.rx.next()

    async def action_rewind(self):
        self.rx.previous()

    async def action_toggle_muted(self):
        self.rx.mute = not self.rx.mute

    async def get_playback_status(self) -> bool:
        return self.rx.is_playback_supported()

    async def update(self):
        try:
            self.play_status = self.rx.play_status()
        except Exception as e:
            self.play_status = None

        available_inputs = {
            raw_name or name
            for name, raw_name
            in self.rx.inputs().get("available_inputs").items()}
        await self.states.update("available_inputs", available_inputs)

    async def get_artist(self):
        if self.play_status:
            return self.play_status.artist

    async def get_album(self):
        if self.play_status:
            return self.play_status.album

    async def get_title(self):
        if self.play_status:
            return self.play_status.song

    
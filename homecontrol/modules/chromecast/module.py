"Chromecast module"

import pychromecast


class Chromecast:
    """The Chromecast item"""
    last_time_jump = 0

    async def init(self):
        """Initialises the Chromecast item"""
        try:
            self.chromecast = pychromecast.Chromecast(
                host=self.cfg["host"], port=self.cfg["port"])
        except pychromecast.error.ChromecastConnectionError:
            return False

        self.media_controller = self.chromecast.media_controller
        self.last_time_jump = vars(
            self.media_controller).get("current_time", 0)
        await self.states.bulk_update(
            playing=vars(
                self.media_controller).get("player_state") == "PLAYING",
            cast_state=self.media_controller.status,
            content_type=self.media_controller.status.content_type,
            metadata=self.media_controller.status.media_metadata,
            volume=int(self.media_controller.status.volume_level * 100)
        )
        self.media_controller.register_status_listener(self)

    async def get_playtime(self):
        """Getter for playtime"""
        await self.states.update(
            "playtime", vars(self.media_controller).get("current_time"))
        return vars(self.media_controller).get("current_time")

    async def set_playtime(self, value):
        """"Setter for playtime"""
        value = max(0, min(value, await self.states.get("duration")))
        self.media_controller.seek(value)
        await self.states.update("playtime", value)
        return {"playtime": value}

    async def get_cast_state(self):
        """Get information about what's currently playing"""
        return vars(self.media_controller.status)

    async def action_pause(self):
        """Action: Pause"""
        self.media_controller.pause()
        return True

    async def get_active(self):
        """Get if Chromecast is active"""
        return self.chromecast.media_controller.is_active

    async def get_playing(self):
        """Getter for playing"""
        return self.chromecast.media_controller.is_playing

    async def set_playing(self, value):
        """Setter for playing"""
        if value:
            self.media_controller.play()
        else:
            self.media_controller.pause()
        await self.states.update("playing", value)
        return {"playing": value}

    async def action_play(self):
        """Action: Play"""
        self.media_controller.play()
        return True

    async def action_play_url(self, url, mime):
        """Action: Play URL"""
        self.media_controller.play_media(url=url, content_type=mime)

    async def action_rewind(self):
        """Action: Rewind"""
        self.media_controller.rewind()
        return True

    async def action_skip(self):
        """Action: Skip"""
        self.media_controller.skip()
        return True

    async def action_stop(self):
        """Action: stop"""
        if self.media_controller.is_active:
            self.media_controller.stop()
        return True

    async def set_volume(self, value):
        """Setter for volume"""
        self.chromecast.set_volume(value / 100)
        return ({"volume": value}
                if await self.states.update("volume", value)
                else {})

    async def set_muted(self, value):
        """Setter for muted"""
        self.chromecast.set_volume_muted(bool(value))
        return ({"muted": value}
                if await self.states.update("muted", value)
                else {})

    async def action_toggle_muted(self):
        """Action: Toggle muted"""
        new_state = not await self.states.get("muted")
        await self.states.set("muted", new_state)

    async def action_quit(self):
        """Action: Quit casting"""
        self.chromecast.quit_app()

    def new_cast_status(self, status):
        """Handle new cast status"""
        self.core.event_engine.broadcast(
            "chromecast_cast_status", status=status)

    def new_media_status(self, status) -> None:
        """Handle new media status"""
        self.core.loop.create_task(self.update_media_status(status))

    async def update_media_status(self, status) -> None:
        """Update media status"""
        self.last_time_jump = status.current_time

        await self.states.bulk_update(
            playtime=status.current_time,
            playing=vars(status).get("player_state") == "PLAYING",
            cast_state=status,
            content_type=status.content_type,
            metadata=status.media_metadata,
            volume=int(status.volume_level * 100),
            duration=status.duration
        )

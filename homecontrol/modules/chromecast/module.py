import pychromecast


class Chromecast:
    last_time_jump = 0

    async def init(self):
        self.cc = pychromecast.Chromecast(
            host=self.cfg["host"], port=self.cfg["port"])
        self.media_controller = self.cc.media_controller
        self.last_time_jump = self.media_controller.__dict__.get(
            "current_time", 0)
        await self.states.update("playing", self.media_controller.__dict__.get("player_state") == "PLAYING")
        await self.states.update("cast_state", self.media_controller.status)
        await self.states.update("content_type", self.media_controller.status.content_type)
        await self.states.update("metadata", self.media_controller.status.media_metadata)
        await self.states.update("volume", int(self.media_controller.status.volume_level * 100))
        self.media_controller.register_status_listener(self)

        @event("chromecast_media_status")
        async def on_status(event, data):
            if data.current_time != self.last_time_jump:
                self.core.event_engine.broadcast("state_change", item=self,
                                                 changes={"playtime": data.current_time})
            self.last_time_jump = data.current_time
            await self.states.update("playing", data.__dict__.get("player_state") == "PLAYING")
            await self.states.update("metadata", data.media_metadata)
            await self.states.update("content_type", data.content_type)
            await self.states.update("cast_state", data)
            await self.states.update("volume", int(data.volume_level * 100))
            await self.states.update("duration", data.duration)

    async def get_playtime(self):
        await self.states.update("playtime", self.media_controller.__dict__.get("current_time"))
        return self.media_controller.__dict__.get("current_time")

    async def set_playtime(self, value):
        value = max(0, min(value, await self.states.get("duration")))
        self.media_controller.seek(value)
        await self.states.update("playtime", value)
        return {"playtime": value}

    async def get_state(self):
        return {
            'metadata_type': self.media_controller.status.metadata_type,
            'title': self.media_controller.status.title,
            'series_title': self.media_controller.status.series_title,
            'season': self.media_controller.status.season,
            'episode': self.media_controller.status.episode,
            'artist': self.media_controller.status.artist,
            'album_name': self.media_controller.status.album_name,
            'album_artist': self.media_controller.status.album_artist,
            'track': self.media_controller.status.track,
            'subtitle_tracks': self.media_controller.status.subtitle_tracks,
            'images': self.media_controller.status.images,
            'supports_pause': self.media_controller.status.supports_pause,
            'supports_seek': self.media_controller.status.supports_seek,
            'supports_stream_volume': self.media_controller.status.supports_stream_volume,
            'supports_stream_mute': self.media_controller.status.supports_stream_mute,
            'supports_skip_forward': self.media_controller.status.supports_skip_forward,
            'supports_skip_backward': self.media_controller.status.supports_skip_backward,
            **self.media_controller.status.__dict__
        }

    async def pause(self):
        self.media_controller.pause()
        return True

    async def get_active(self):
        return self.cc.media_controller.is_active

    async def get_playing(self):
        return self.cc.media_controller.is_playing

    async def set_playing(self, value):
        if value:
            self.media_controller.play()
        else:
            self.media_controller.pause()
        await self.states.update("playing", value)
        return {"playing": value}

    async def play(self):
        self.media_controller.play()
        return True

    async def play_url(self, url, mime):
        self.media_controller.play_media(url=url, content_type=mime)

    async def rewind(self):
        self.media_controller.rewind()
        return True

    async def skip(self):
        self.media_controller.skip()
        return True

    async def stop(self):
        if self.media_controller.is_active:
            self.media_controller.stop()
        return True

    async def set_volume(self, value):
        self.cc.set_volume(value / 100)
        return {"volume": value} if await self.states.update("volume", value) else {}

    async def set_muted(self, value):
        self.cc.set_volume_muted(bool(value))
        return {"muted": value} if await self.states.update("muted", value) else {}

    async def toggle_muted(self):
        new_state = not (await self.states.get("muted"))
        await self.states.set("muted", new_state)

    async def quit(self):
        self.cc.quit_app()

    def new_cast_status(self, status):
        self.core.event_engine.broadcast(
            "chromecast_cast_status", status=status)

    def new_media_status(self, status):
        self.core.event_engine.broadcast(
            "chromecast_media_status", status=status)

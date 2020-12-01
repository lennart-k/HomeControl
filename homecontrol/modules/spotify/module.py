"""spotify module"""
import asyncio
import logging
import time
from functools import partial
from typing import Any, Dict
from uuid import uuid4

import spotipy
import voluptuous as vol
from aiohttp import web
from spotipy.oauth2 import SpotifyOAuth

from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import ModuleDef
from homecontrol.dependencies.item_manager import StorageEntry
from homecontrol.dependencies.storage import Storage
from homecontrol.modules.media_player.module import MediaPlayer

LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(vol.Or({
    vol.Required("client-id"): str,
    vol.Required("secret"): str,
    vol.Required("redirect-uri"): str,
    vol.Required("scopes", default=[
        "user-read-playback-state", "user-modify-playback-state"
    ]): [str]
}, False))


class Module(ModuleDef):
    """The spotify module"""
    auth: SpotifyOAuth

    async def init(self) -> None:
        self.cfg = await self.core.cfg.register_domain(
            "spotify", schema=CONFIG_SCHEMA, default=False)
        if not self.cfg:
            return
        self.auth = SpotifyOAuth(
            self.cfg["client-id"], self.cfg["secret"],
            self.cfg["redirect-uri"], scope=",".join(self.cfg["scopes"]))
        self.core.event_bus.register("http_add_api_routes")(self.auth_routes)

    async def auth_routes(self, event, router: web.RouteTableDef) -> None:
        """OAuth routes for setup"""
        @router.get("/spotify/callback")
        async def spotify_callback(request: web.Request) -> web.Response:
            if "code" not in request.query:
                return web.Response(
                    body="Authorization code missing", status=400)

            access_token = await self.core.loop.run_in_executor(
                None,
                partial(
                    self.auth.get_access_token,
                    request.query["code"], as_dict=True, check_cache=False))

            user = await self.core.loop.run_in_executor(
                None,
                spotipy.Spotify(
                    auth=access_token["access_token"]).current_user)
            identifier = f"spotify_{user['id']}"

            await self.core.item_manager.register_entry(StorageEntry(
                unique_identifier=identifier,
                type="spotify.Spotify",
                enabled=True,
                cfg={
                    "refresh_token": access_token["refresh_token"],
                    "scope": access_token["scope"]
                },
                name=f"Spotify {user['display_name']}"
            ), override=True)

            raise web.HTTPFound(
                f"https://lennartk.duckdns.org/frontend/item/{identifier}")

        @router.get("/spotify/authorize")
        async def spotify_redirect(request: web.Request) -> web.Response:
            auth_url = self.auth.get_authorize_url(state=uuid4().hex)

            raise web.HTTPFound(auth_url)


class Spotify(MediaPlayer):
    """A Spotify item"""
    module: "Module"
    token: Dict[str, Any]
    refresh_handle: asyncio.TimerHandle
    update_task: asyncio.Task
    config_schema = vol.Schema({
        vol.Required("refresh_token"): str,
        vol.Required("scope"): str,
        vol.Optional("access_token"): str,
        vol.Optional("token_type"): str,
        vol.Optional("expires_in"): int,
        vol.Optional("expires_at"): int,
    })

    async def init(self) -> None:
        self.auth = self.module.auth
        self.storage = Storage(
            f"item_data/{self.unique_identifier}", 1,
            core=self.core,
            storage_init=lambda: {})

        self.token = self.storage.load_data() or self.cfg

        self._keep_access_token_new()
        self.update_task = self.core.loop.create_task(
            self._keep_states_updated())
        self.api = spotipy.Spotify(client_credentials_manager=self)

    async def stop(self) -> None:
        self.refresh_handle.cancel()
        self.update_task.cancel()

    def get_access_token(self) -> Dict[str, Any]:
        """Returns the access token for spotipy"""
        return self.token["access_token"]

    def _keep_access_token_new(self) -> None:
        if (not self.token
                or self.token.get("expires_at", 0) < time.time() + 600):

            LOGGER.info("Requesting new access token")
            self.token = self.auth.refresh_access_token(
                self.cfg["refresh_token"])
            self.storage.schedule_save(self.token)

        next_call = (
            self.core.loop.time()
            + self.token["expires_at"] - time.time() - 60)
        self.refresh_handle = self.core.loop.call_at(
            next_call, self._keep_access_token_new)

    async def _keep_states_updated(self) -> None:
        while True:
            await self._update_states()
            await asyncio.sleep(2)

    async def _update_states(self) -> None:
        # pylint: disable=protected-access
        playback = await self.core.loop.run_in_executor(
            None, partial(
                self.api._get,
                "me/player", additional_types="track,episode"))

        if not playback or not playback.get("item"):
            return self.states.bulk_update(
                playing=False,
                volume=0,
                title=None,
                artist=None,
                album=None,
                position=None,
                duration=None,
                cover=None
            )

        item = playback["item"]
        device = playback["device"]

        state_data = {
            "playing": playback["is_playing"],
            "volume": device.get("volume_percent", 0),
            "title": item["name"],
            "position": playback["progress_ms"] / 1000,
            "duration": item["duration_ms"] / 1000
        }

        if item["type"] == "track":
            images = item["album"]["images"]
            state_data.update({
                "artist": ", ".join(
                    artist["name"] for artist in item.get("artists", [])),
                "album": item["album"]["name"],
                "cover": images[0]["url"] if images else None
            })

        elif item["type"] == "episode":
            images = item["images"]
            state_data.update({
                "artist": item["show"]["publisher"],
                "album": item["show"]["name"],
                "cover": images[0]["url"] if images else None
            })

        self.states.bulk_update(**state_data)

    async def set_playing(self, playing: bool) -> Dict[str, Any]:
        await self.core.loop.run_in_executor(
            None,
            self.api.start_playback if playing else self.api.pause_playback)
        return {"playing": playing}

    async def set_volume(self, volume: int) -> Dict[str, Any]:
        await self.core.loop.run_in_executor(None, self.api.volume, volume)
        return {"volume": volume}

    async def set_position(self, position: int) -> Dict[str, Any]:
        await self.core.loop.run_in_executor(
            None, self.api.seek_track, position * 1000)
        return {"position": position}

    @action("play")
    async def action_play(self):
        await self.states.set("playing", True)

    @action("pause")
    async def action_pause(self):
        await self.states.set("playing", False)

    @action("stop")
    async def action_stop(self):
        await self.states.set("playing", False)

    @action("next")
    async def action_next(self):
        await self.core.loop.run_in_executor(
            None, self.api.next_track)

    @action("previous")
    async def action_previous(self):
        await self.core.loop.run_in_executor(
            None, self.api.previous_track)

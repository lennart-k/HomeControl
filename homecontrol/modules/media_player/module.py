"""media_player module"""
import logging
from typing import Any, Dict

import voluptuous as vol

from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef

LOGGER = logging.getLogger(__name__)

SPEC = {
    "name": "media_player",
    "description": "Provides a basic media_player item"
}


class MediaPlayer(Item):
    """media_player Item"""
    type = "media_player.MediaPlayer"

    playing = StateDef()
    volume = StateDef()
    title = StateDef()
    artist = StateDef()
    album = StateDef()
    content_type = StateDef()
    cover = StateDef()
    position = StateDef()
    duration = StateDef()

    @playing.setter(vol.Schema(bool))
    async def set_playing(self, playing: bool) -> Dict[str, Any]:
        """Sets the playing state"""
        raise NotImplementedError()

    @volume.setter(vol.Schema(int))
    async def set_volume(self, volume: int) -> Dict[str, Any]:
        """Sets the volume state"""
        raise NotImplementedError()

    @position.setter(vol.Schema(int))
    async def set_position(self, position: int) -> Dict[str, Any]:
        """Sets the position state"""
        raise NotImplementedError()

    @action("play")
    async def action_play(self):
        """Action play"""
        raise NotImplementedError()

    @action("pause")
    async def action_pause(self):
        """Action pause"""
        raise NotImplementedError()

    @action("stop")
    async def action_stop(self):
        """Action stop"""
        raise NotImplementedError()

    @action("next")
    async def action_next(self):
        """Action next"""
        raise NotImplementedError()

    @action("previous")
    async def action_previous(self):
        """Action previous"""
        raise NotImplementedError()

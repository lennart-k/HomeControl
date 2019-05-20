"""Support for statistics from socialblade.com"""

import requests
from lxml import html

LOOKUP_URL = "https://bastet.socialblade.com/{platform}/lookup"

NAME_PATH = '//*[@id="rawUser"]/text()'
NAME_URL = "https://socialblade.com/{platform}/user/{name}/realtime"


class TwitchFollowers:
    """Followers on Twitch"""
    async def init(self) -> bool:
        """Initialise the item"""
        self.cfg.setdefault("rawname", self._get_rawname())
        if not self.cfg["rawname"]:
            return False
        tick(self.cfg["update_interval"])(self.update_followers)

    async def update_followers(self):
        """Update the current state"""
        await self.states.update("followers", int(requests.get(
            LOOKUP_URL.format(platform="twitch"),
            params={"query": self.cfg["rawname"]}).content))

    def _get_rawname(self):
        content = html.fromstring(requests.get(NAME_URL.format(
            name=self.cfg["name"], platform="twitch")).content)
        result = content.xpath(NAME_PATH)
        if result:
            return str(result[0])
        return None


class YouTubeFollowers:
    """Followers on YouTube"""
    async def init(self) -> bool:
        """Initialise the item"""
        self.cfg.setdefault("rawname", self._get_rawname())
        if not self.cfg["rawname"]:
            return False
        tick(self.cfg["update_interval"])(self.update_followers)

    async def update_followers(self):
        """Update the current state"""
        await self.states.update("followers", int(requests.get(
            LOOKUP_URL.format(platform="youtube"),
            params={"query": self.cfg["rawname"]}).content))

    def _get_rawname(self):
        content = html.fromstring(requests.get(NAME_URL.format(
            name=self.cfg["name"], platform="youtube")).content)
        result = content.xpath(NAME_PATH)
        if result:
            return str(result[0])
        return None


class TwitterFollowers:
    """Followers on Twitter"""
    async def init(self) -> bool:
        """Initialise the item"""
        tick(self.cfg["update_interval"])(self.update_followers)

    async def update_followers(self):
        """Update the current state"""
        await self.states.update(
            "followers", int(requests.get(
                LOOKUP_URL.format(platform="twitter"),
                params={"query": self.cfg["name"]}).content))

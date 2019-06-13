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

    async def poll_followers(self):
        """Polls the current state"""
        response = requests.get(
            LOOKUP_URL.format(platform="twitch"),
            params={"query": self.cfg["rawname"]})
        return int(response.content)

    async def update_followers(self) -> None:
        """Updates the current state"""
        await self.states.update("followers", await self.poll_followers())

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

    async def poll_followers(self):
        """Polls the current state"""
        response = requests.get(
            LOOKUP_URL.format(platform="youtube"),
            params={"query": self.cfg["rawname"]})
        return int(response.content)

    async def update_followers(self) -> None:
        """Updates the current state"""
        await self.states.update("followers", await self.poll_followers())

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

    async def poll_followers(self):
        """Polls the current state"""
        response = requests.get(
            LOOKUP_URL.format(platform="twitter"),
            params={"query": self.cfg["name"]})
        return int(response.content)

    async def update_followers(self) -> None:
        """Updates the current state"""
        await self.states.update("followers", await self.poll_followers())

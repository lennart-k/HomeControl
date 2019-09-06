"""Support for statistics from socialblade.com"""

import logging

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

LOOKUP_URL = "https://bastet.socialblade.com/{platform}/lookup"

NAME_PATH = '//*[@id="rawUser"]/text()'
NAME_URL = "https://socialblade.com/{platform}/user/{name}/realtime"
HEADERS = {"User-Agent": "HomeControl"}


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
            params={"query": self.cfg["rawname"]},
            headers=HEADERS)
        return int(response.content)

    async def update_followers(self) -> None:
        """Updates the current state"""
        await self.states.update("followers", await self.poll_followers())

    def _get_rawname(self):
        response = requests.get(NAME_URL.format(
            name=self.cfg["name"], platform="twitch"),
                                headers=HEADERS)

        if response.status_code != 200:
            LOGGER.error("Could not resolve rawname for %s: HTTP %s",
                         self.cfg["name"], response.status_code)
            return
        soup = BeautifulSoup(response.content, "html.parser")
        result = soup.find(id="rawUser")
        if result:
            return result.get_text()
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
            params={"query": self.cfg["rawname"]},
            headers=HEADERS)
        return int(response.content)

    async def update_followers(self) -> None:
        """Updates the current state"""
        await self.states.update("followers", await self.poll_followers())

    def _get_rawname(self):
        response = requests.get(NAME_URL.format(
            name=self.cfg["name"], platform="youtube"),
                                headers=HEADERS)

        if response.status_code != 200:
            LOGGER.error("Could not resolve rawname for %s: HTTP %s",
                         self.cfg["name"], response.status_code)
            return
        soup = BeautifulSoup(response.content, "html.parser")
        result = soup.find(id="rawUser")
        if result:
            return result.get_text()
        return None


class TwitterFollowers:
    """Followers on Twitter"""
    async def init(self) -> bool:
        """Initialise the item"""

    async def poll_followers(self):
        """Polls the current state"""
        response = requests.get(
            LOOKUP_URL.format(platform="twitter"),
            params={"query": self.cfg["name"]},
            headers=HEADERS)
        return int(response.content)

    async def update_followers(self) -> None:
        """Updates the current state"""
        await self.states.update("followers", await self.poll_followers())

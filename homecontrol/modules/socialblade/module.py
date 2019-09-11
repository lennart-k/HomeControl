"""Support for statistics from socialblade.com"""

import logging

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

LOOKUP_URL = "https://bastet.socialblade.com/{platform}/lookup"

NAME_PATH = '//*[@id="rawUser"]/text()'
NAME_URL = "https://socialblade.com/{platform}/user/{name}/realtime"
HEADERS = {"User-Agent": "HomeControl"}


def get_rawname(name: str, platform: str) -> str:
    """
    Gets a user id from a username
    """
    response = requests.get(NAME_URL.format(
        name=name, platform=platform),
        headers=HEADERS)

    if response.status_code != 200:
        LOGGER.error("Could not resolve rawname for %s: HTTP %s",
                     name, response.status_code)
        return
    soup = BeautifulSoup(response.content, "html.parser")
    result = soup.find(id="rawUser")
    if result:
        return result.get_text()
    return None


class TwitchFollowers:
    """Followers on Twitch"""
    async def init(self) -> bool:
        """Initialise the item"""
        self.cfg.setdefault("rawname", get_rawname(
            self.cfg["name"], "twitch"
        ))
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


class YouTubeFollowers:
    """Followers on YouTube"""
    async def init(self) -> bool:
        """Initialise the item"""
        self.cfg.setdefault("rawname", get_rawname(
            self.cfg["name"], "youtube"
        ))
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

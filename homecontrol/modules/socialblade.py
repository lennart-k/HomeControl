from lxml import html
import requests

SPEC = """

meta: SocialBlade
description: Track follower stats on YouTube, Twitch, Twitter and Instagram

items:
  YouTubeFollowers:
    config_schema:
      !vol/Any [rawname, name]: !type/str
      !vol/Required { schema: update_interval, default: 10 }: !type/int

    state:
      followers:
        type: Integer
        default: 0

    actions:
      update_followers: update_followers

  TwitchFollowers:
    config_schema:
      !vol/Any [rawname, name]: !type/str
      !vol/Required { schema: update_interval, default: 10 }: !type/int

    state:
      followers:
        type: Integer
        default: 0

    actions:
      update_followers: update_followers

  TwitterFollowers:
    config_schema:
      !vol/Required { schema: name }: !type/str
      !vol/Required { schema: update_interval, default: 10 }: !type/int

    state:
      followers:
        type: Integer
        default: 0

    actions:
      update_followers: update_followers


"""

LOOKUP_URL = "https://bastet.socialblade.com/{platform}/lookup"

# NAME_PATH = '//body/div[@id="profile"]/div[@id="sub-profile"]/div/div/div/p[@id="rawUser"]/text()'
NAME_PATH = '//*[@id="rawUser"]/text()'
NAME_URL = "https://socialblade.com/{platform}/user/{name}/realtime"


class TwitchFollowers:
    async def init(self) -> bool:
        self.cfg.setdefault("rawname", self.get_rawname())
        if not self.cfg["rawname"]:
            return False
        tick(self.cfg["update_interval"])(self.update_followers)

    async def update_followers(self):
        await self.states.update("followers", int(requests.get(LOOKUP_URL.format(platform="twitch"), params={"query": self.cfg["rawname"]}).content))

    def get_rawname(self):
        content = html.fromstring(requests.get(NAME_URL.format(name=self.cfg["name"], platform="twitch")).content)
        result = content.xpath(NAME_PATH)
        if result:
            return str(result[0])
        return None


class YouTubeFollowers:
    async def init(self) -> bool:
        self.cfg.setdefault("rawname", self.get_rawname())
        if not self.cfg["rawname"]:
            return False
        tick(self.cfg["update_interval"])(self.update_followers)

    async def update_followers(self):
        await self.states.update("followers", int(requests.get(LOOKUP_URL.format(platform="youtube"), params={"query": self.cfg["rawname"]}).content))

    def get_rawname(self):
        content = html.fromstring(requests.get(NAME_URL.format(name=self.cfg["name"], platform="youtube")).content)
        result = content.xpath(NAME_PATH)
        if result:
            return str(result[0])
        return None

class TwitterFollowers:
    async def init(self) -> bool:
        tick(self.cfg["update_interval"])(self.update_followers)

    async def update_followers(self):
        await self.states.update("followers", int(requests.get(LOOKUP_URL.format(platform="twitter"), params={"query": self.cfg["name"]}).content))

"""Pushbullet module"""

import json
import requests
import voluptuous as vol

from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.action_engine import action

SPEC = {
    "name": "Pushbullet"
}

BASE_URL = "https://api.pushbullet.com/v2"
PUSH_URL = BASE_URL + "/pushes"
ME_URL = BASE_URL + "/users/me"


class Pushbullet(Item):
    """The Pushbullet item"""
    config_schema = vol.Schema({
        vol.Required("access_token"): str
    }, extra=vol.ALLOW_EXTRA)

    async def init(self):
        """Initialise Pushbullet"""
        try:
            return requests.get(ME_URL, headers={
                "Access-Token": self.cfg["access_token"],
                "Content-Type": "application/json"
            }).status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    @action("send_message")
    async def send_message(self, **data):
        """Sends a message"""
        data = {
            "type": "note",
            **data
        }
        requests.post(PUSH_URL, json.dumps(data), headers={
            "Access-Token": self.cfg["access_token"],
            "Content-Type": "application/json"
        })

import requests
import json

BASE_URL = "https://api.pushbullet.com/v2"
PUSH_URL = BASE_URL+"/pushes"
ME_URL = BASE_URL+"/users/me"


class Pushbullet:
    async def init(self):
         working = requests.get(ME_URL, headers={
            "Access-Token": self.cfg["access_token"],
            "Content-Type": "application/json"
        }).status_code == 200

    async def send_message(self, **data):
        data = {
            "type": "note",
            **data
        }
        result = requests.post(PUSH_URL, json.dumps(data), headers={
            "Access-Token": self.cfg["access_token"],
            "Content-Type": "application/json"
        }).json()

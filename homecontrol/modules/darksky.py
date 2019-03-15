import requests
import asyncio


SPEC = """
meta:
  name: DarkSky
  description: A weather provider

items:
  WeatherProvider:
    config_fields:
      token:
        required: True
        type: String

      location:
        required: True
        type: String

      language:
        type: String
        default: en

      units:
        type: String
        default: auto

      update_interval:
        type: Integer
        default: 300

    state:
      weather_data:
        type: WeatherData
        default: None

"""

EXCLUDE = ["minutely", "hourly"]
URL = "https://api.darksky.net/forecast/{token}/{location}?lang={lang}&units={units}"

class WeatherProvider:
    async def init(self):
        tick(self.cfg["update_interval"])(self.fetch_weather)

    async def fetch_weather(self):
        request = requests.get(URL.format(token=self.cfg["token"], lang=self.cfg["language"], units=self.cfg["units"], exclude=",".join(EXCLUDE), location=self.cfg["location"]))
        data = request.json()
        if not data.get("flags", {}).get("darksky-unavailable"):
            await self.states.update("weather_data", WeatherData(data, "DarkSky", self.cfg["location"]))

class WeatherData:
    def __init__(self, data, provider, location):
        self.data = data
        self.provider = provider
        self.location = location

    def __repr__(self):
        return f"<WeatherData in {self.location} from {self.provider}>"
"""Weather forecast using DarkSky"""

import requests

SPEC = """
meta:
  name: DarkSky
  description: A weather provider

items:
  WeatherProvider:
    config_schema:
      !vol/Required {schema: token}:
        !type/str
      
      !vol/Required {schema: location}:
        !type/str
      
      !vol/Required {schema: language}:
        !vol/All
          - !type/str
          - !vol/Any [ar, az, be, bg, bs, ca, cs, da, de, el, en, es, et, fi, fr, he, hr, hu, id, is, it, ja, ka, ko, kw, lv, nb, nl, no, pl, pt, ro, ru, sk, sl, sr, sv, tet, tr, uk, x-pig-latin, zh, zh-tw]

      !vol/Required {schema: units, default: auto}:
        !vol/All
          - !type/str
          - !vol/Any [auto, ca, uk2, us, si]

      !vol/Required {schema: update_interval, default: 300}:
        !type/int
      

    states:
      weather_data:
        type: WeatherData
        default: None

"""

EXCLUDE = ["minutely", "hourly"]
URL = "https://api.darksky.net/forecast/{token}/{location}?lang={lang}&units={units}&exclude={exclude}"


class WeatherProvider:
    """The WeatherProvider item"""
    async def init(self):
        """Initialise the WeatherProvider item"""
        tick(self.cfg["update_interval"])(self.fetch_weather)

    async def fetch_weather(self):
        """Fetch the weather from the DarkSky API"""
        request = requests.get(URL.format(token=self.cfg["token"],
                                          lang=self.cfg["language"],
                                          units=self.cfg["units"],
                                          exclude=",".join(EXCLUDE),
                                          location=self.cfg["location"]))
        data = request.json()
        if not data.get("flags", {}).get("darksky-unavailable"):
            await self.states.update(
                "weather_data", WeatherData(data, "DarkSky", self.cfg["location"]))


class WeatherData:
    """A class holding the weather data"""
    def __init__(self, data, provider, location):
        self.data = data
        self.provider = provider
        self.location = location

    def __repr__(self):
        return f"<WeatherData in {self.location} from {self.provider}>"

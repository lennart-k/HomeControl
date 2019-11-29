"""Support for Helios ventilations with an easyControls interface"""

import requests

from homecontrol.dependencies.entity_types import Item


class HeliosVentilation(Item):
    """The ventilation item"""
    async def init(self):
        """Initialise the HeliosVentilation item"""
        self.core.tick_engine.tick(30)(self.ensure_login)

    async def ensure_login(self) -> None:
        """
        The Helios easyControls system has a global login management.
        That means to keep the requests working
        we just need to send a login request every ten minutes.
        """
        requests.post(
            f"http://{self.cfg['host']}/info.htm",
            data={'v00402': 'helios'})

    async def start_party(self,
                          duration: int = None,
                          party_level: int = None) -> None:
        """Action: Start party mode"""
        duration = duration or self.cfg["default_party_duration"]
        party_level = party_level or self.cfg["default_party_level"]
        requests.post(f"http://{self.cfg['host']}/party.htm", data={
            "v00091": duration,
            "v00092": party_level,
            "v00093": 0,
            "v00094": 1  # Activate party mode
        })

    async def stop_party(self) -> None:
        """Action: Stop party mode"""
        requests.post(f"http://{self.cfg['host']}/party.htm", data={
            "v00094": 0,  # Deactivate party mode
        })

    async def set_speed(self, value: int) -> dict:
        """Setter for speed"""
        await self.states.update("speed", value)
        requests.post(f"http://{self.cfg['host']}/index.htm", data={
            "v00102": value,  # Speed register
        })
        return {"speed": value}

    async def stop(self) -> None:
        """Stops the item"""
        self.core.tick_engine.remove_tick(30, self.ensure_login)

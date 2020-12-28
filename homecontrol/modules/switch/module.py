"""switch module"""
import logging
from typing import Any, Dict

import voluptuous as vol

from homecontrol.dependencies.action_decorator import action
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef

LOGGER = logging.getLogger(__name__)

SPEC = {
    "name": "switch",
    "description": "A basic switch type"
}


class Switch(Item):
    """A basic switch item"""
    type = "switch.Switch"
    on = StateDef()

    @on.setter(schema=vol.Schema(bool))
    async def set_on(self, value: bool) -> Dict[str, Any]:
        """Setter for state on"""
        return {"on": value}

    @action("turn_on")
    async def turn_on(self) -> None:
        """Turns the switch on"""
        await self.states.set("on", True)

    @action("turn_off")
    async def turn_off(self) -> None:
        """Turns the switch off"""
        await self.states.set("on", False)

    @action("toggle")
    async def action_toggle(self) -> None:
        """Toggles the switch"""
        await self.states.set("on", not await self.states.get("on"))

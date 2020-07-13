"""A module for the old Intertechno switches"""

from typing import Dict

import voluptuous as vol
from homecontrol.const import ItemStatus
from homecontrol.dependencies.action_engine import action
from homecontrol.dependencies.entity_types import Item, ModuleDef
from homecontrol.dependencies.state_proxy import StateDef

from .dependencies.intertechno_codes import from_code, to_code


class Module(ModuleDef):
    """The module translating RF codes to Intertechno codes"""
    async def init(self):
        """Initialise the module"""
        @self.core.event_engine.register("rf_code_received")
        async def on_rf_code(event, code, length):
            """Handle RF code"""
            if length == 12:
                it_code = from_code(code)
                if it_code:
                    self.core.event_engine.broadcast(
                        "intertechno_code_received",
                        **dict(zip(("house", "id", "state"), it_code)))


class IntertechnoSwitch(Item):
    """An Intertechno switch"""
    cfg: dict
    on = StateDef(default=False)
    config_schema = vol.Schema({
        vol.Required("house"): vol.All(
            vol.Coerce(type=str),
            vol.Upper,
            vol.Any("A", "B", "C", "D", "E", "F", "G", "H",
                    "J", "K", "L", "M", "N", "O", "P", "Q")),
        vol.Required("id"): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=16)),
        vol.Required("433mhz_tx_adapter"): str
    }, extra=vol.ALLOW_EXTRA)

    async def init(self):
        """Initialise the switch"""

        self.rf_adapter = self.core.item_manager.get_item(
            self.cfg["433mhz_adapter"])

        if not self.rf_adapter:
            return ItemStatus.WAITING_FOR_DEPENDENCY

        @self.core.event_engine.register("intertechno_code_received")
        async def on_it_code(event, house, identifier, state):
            if (self.cfg["house"].lower(), self.cfg["id"]) \
                    == (house, identifier):
                self.states.update("on", state)

    @action("toggle")
    async def toggle_on(self):
        """Toggle on"""
        return await self.states.set("on", not await self.states.get("on"))

    # pylint: disable=invalid-name
    @on.setter(schema=vol.Schema(vol.All(
        vol.Any(bool, int), vol.Coerce(type=bool)
    )))
    async def set_on(self, on: bool) -> Dict[str, bool]:
        """Setter for on state"""
        await self.rf_adapter.send_code(
            to_code(self.cfg["house"], self.cfg["id"], on))
        return {"on": on}

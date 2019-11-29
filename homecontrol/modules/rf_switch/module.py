"""A module for the old Intertechno switches"""

from .dependencies.intertechno_codes import from_code, to_code

from homecontrol.dependencies.entity_types import Item


class Module:
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

    async def init(self):
        """Initialise the switch"""

        @self.core.event_engine.register("intertechno_code_received")
        async def on_it_code(event, house, identifier, state):
            if (self.cfg["house"].lower(), self.cfg["id"]) \
                    == (house, identifier):
                await self.states.update("on", state)

    # pylint: disable=invalid-name
    async def switch(self, on):
        """Setter for on"""
        await self.cfg["433mhz_tx_adapter"].send_code(
            to_code(self.cfg["house"], self.cfg["id"], on))
        return {"on": on}

    async def toggle_on(self):
        """Toggle on"""
        return await self.states.set("on", not await self.states.get("on"))

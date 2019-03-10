from dependencies.intertechno_codes import from_code, to_code


class Module:
    async def init(self):
        @event("rf_code_received")
        async def on_rf_code(code, length):
            if length == 12:
                it_code = from_code(code)
                if it_code:
                    self.core.event_engine.broadcast("intertechno_code_received", *it_code)


class IntertechnoSwitch:
    cfg: dict
    on: bool

    async def init(self):
        self.on = await self.states.get("on")

        @event("intertechno_code_received")
        async def on_it_code(house, id, state):
            if (self.cfg["house"].lower(), self.cfg["id"]) == (house, id):
                await self.states.update("on", state)

    async def switch(self, on):
        self.on = on
        await self.cfg["433mhz_tx_adapter"].send_code(to_code(self.cfg["house"], self.cfg["id"], on))
        return {"on": on}

    async def toggle_on(self):
        return await self.states.set("on", not self.on)

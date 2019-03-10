class Module:
    pass


class DummySwitch:
    async def init(self):
        pass

    async def set_on(self, value):
        print(value)
        await self.states.update("on", value)
        return {"on": value}

    async def toggle(self):
        new = not await self.states.get("on")
        await self.states.set("on", new)
        return {"on": new}

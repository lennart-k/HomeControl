from pigpio import pi
from dependencies.data_types import Color


class RGBLight:
    cfg: dict
    mode: str
    gpio: pi

    async def init(self):
        self.gpio = self.cfg["pigpio_adapter"].pigpio
        await self.apply_color()

    async def set_color(self, color: Color) -> dict:
        await self.states.update("color", color)
        await self.apply_color()
        return {"color": color}

    async def apply_color(self) -> Color:
        color = await self.states.get("color")
        color_tup = color.to_tuple()
        for pin, val in ((self.cfg["pin_r"], color_tup[0]), (self.cfg["pin_g"], color_tup[1]), (self.cfg["pin_b"], color_tup[2])):
            self.gpio.set_PWM_dutycycle(pin, val)
        return color

    async def set_mode(self, mode: str) -> dict:
        if mode == "static":
            return {"mode": mode, "color": await self.apply_color()}
        return {"mode": mode}

    async def set_on(self, value: bool) -> dict:
        if value:
            return {"on": True, "color": await self.apply_color()} if await self.states.update("on", value) else {}
        else:
            for pin in (self.cfg["pin_r"], self.cfg["pin_g"], self.cfg["pin_b"]):
                self.gpio.set_PWM_dutycycle(pin, 0)
            return {"on": False} if await self.states.update("on", value) else {}

    async def toggle_on(self):
        await self.set_on(not await self.states.get("on"))

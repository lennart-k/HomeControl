from pigpio import pi
from dependencies.data_types import Color
import colorsys


class RGBLight:
    cfg: dict
    mode: str
    gpio: pi

    async def init(self):
        self.gpio = self.cfg["pigpio_adapter"].pigpio
        await self.states.set("color", Color.from_rgb((self.gpio.get_PWM_dutycycle(pin) for pin in (self.cfg["pin_r"], self.cfg["pin_g"], self.cfg["pin_b"]))))
        await self.apply_color()

    async def set_color(self, color: Color) -> dict:
        await self.apply_color(color)
        if not await self.states.get("on"):
            return {"color": color, "on": True}
        return {"color": color}

    async def apply_color(self, color: Color = None) -> Color:
        color = color or await self.states.get("color")
        color_tup = color.rgb
        for pin, val in ((self.cfg["pin_r"], color_tup[0]), (self.cfg["pin_g"], color_tup[1]), (self.cfg["pin_b"], color_tup[2])):
            self.gpio.set_PWM_dutycycle(pin, val)
        return color

    async def set_mode(self, mode: str) -> dict:
        if mode == "static":
            return {"mode": mode, "color": await self.apply_color()}
        return {"mode": mode}

    async def set_on(self, value: bool) -> dict:
        if value:
            return {"on": True, "color": await self.apply_color()} if not await self.states.get("on") else {}
        else:
            await self.apply_color(Color((0, 0, 0)))
            return {"on": False}

    async def toggle_on(self):
        await self.set_on(not await self.states.get("on"))

    async def set_hue(self, value):
        color = await self.states.get("color")
        color.h = value
        await self.set_color(color)

    async def set_saturation(self, value):
        color = await self.states.get("color")
        color.s = value
        await self.set_color(color)

    async def set_brightness(self, value):
        color = await self.states.get("color")
        color.l = value
        await self.set_color(color)

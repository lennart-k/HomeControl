from pigpio import pi
from dependencies.data_types import Color
import colorsys


class RGBLight:
    cfg: dict
    mode: str
    gpio: pi

    async def init(self):
        self.gpio = self.cfg["pigpio_adapter"].pigpio
        await self.apply_color()

    async def set_color(self, color: Color) -> dict:
        await self.apply_color(color)
        if not await self.states.get("on"):
            return {"color": color, "on": True}
        return {"color": color}

    async def apply_color(self, color: Color = None) -> Color:
        color = color or await self.states.get("color")
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
            return {"on": True, "color": await self.apply_color()} if not await self.states.get("on") else {}
        else:
            await self.apply_color(Color.from_data((0, 0, 0)))
            return {"on": False}

    async def toggle_on(self):
        await self.set_on(not await self.states.get("on"))

    async def set_brightness(self, value):
        h, _, s = colorsys.rgb_to_hls(*(float(val)/255 for val in (await self.states.get("color")).to_tuple()))
        l = float(value)/255
        await self.set_color(Color(*(round(val*255) for val in colorsys.hls_to_rgb(h, l, s))))

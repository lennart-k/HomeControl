"""Module containing the pigpio adapter"""

import asyncio
from contextlib import suppress
import pigpio

from homecontrol.dependencies.throttle_function import throttle
from homecontrol.core import Core
from homecontrol.dependencies.data_types import Color

# pylint: disable=import-error
from dependencies.lcd import LCD


class PiGPIOAdapter:
    """The PiGPIO adapter"""
    cfg: dict
    pigpio: pigpio.pi
    core: Core

    async def init(self):
        """Initialise the adapter"""
        done, pending = await asyncio.wait(
            {self.core.loop.run_in_executor(None, self.init_pigpio)},
            timeout=2)
        if pending or not self.pigpio.connected:
            return False

    def init_pigpio(self):
        """Initialise PiGPIO"""
        self.pigpio = pigpio.pi(
            self.cfg["host"], self.cfg["port"], show_errors=False)

    async def stop(self):
        """Stop the adapter"""
        await asyncio.gather(*self.core.event_engine.broadcast(
            "pigpio_closing", pigpio=self.pigpio))
        self.pigpio.stop()


class BinaryOutput:
    """A binary output"""
    cfg: dict
    core: Core

    async def init(self):
        """Initialise the output"""
        self.pigpio: pigpio.pi = self.cfg["pigpio_adapter"].pigpio
        self.pigpio.set_mode(self.cfg["pin"], 1)
        self.pigpio.write(
            self.cfg["pin"],
            not (await self.states.get("on")) ^ self.cfg["on_state"])

    async def set_on(self, value: bool) -> dict:
        """Setter for value"""
        self.pigpio.write(self.cfg["pin"], not value ^ self.cfg["on_state"])

        return {"on": value}

    async def toggle_on(self):
        """Action: toggle"""
        return await self.states.set("on", not await self.states.get("on"))


class Button:
    """A button that can also toggle"""
    cfg: dict
    core: Core

    async def init(self):
        """Initialise the button"""
        self.pigpio: pigpio.pi = self.cfg["pigpio_adapter"].pigpio
        self.pigpio.set_mode(self.cfg["pin"], pigpio.INPUT)
        self._cb = self.pigpio.callback(
            self.cfg["pin"], pigpio.EITHER_EDGE, self.callback)

    @throttle(s=0.05)
    def callback(self, pin, reading, timestamp) -> None:
        """Callback that updates the on state"""
        async def _async_callback() -> bool:
            if not self.cfg["toggle"]:
                value = not self.cfg["pull_up"] ^ reading
                if not value == await self.states.get("value"):
                    await self.states.update("value", value)
                    return True
            else:
                if not self.cfg["pull_up"] ^ reading:
                    await self.states.update(
                        "value", not await self.states.get("value"))
                    return True

        asyncio.run_coroutine_threadsafe(
            _async_callback(), loop=self.core.loop)

    async def stop(self):
        """Stop listening"""
        with suppress(AttributeError, ConnectionResetError):
            # pigpio socket already closed
            self._cb.cancel()


class I2CLCD:
    """A 2x16 I²C display for PiGPIO"""
    async def init(self):
        """Initialise the display"""
        self.pigpio: pigpio.pi = self.cfg["pigpio_adapter"].pigpio
        self.lcd = LCD(pi=self.pigpio,
                       bus=self.cfg["bus"],
                       addr=self.cfg["address"],
                       backlight_on=await self.states.get("backlight"))

    async def set_backlight(self, value: bool) -> dict:
        """Set the backlight to on or off"""
        self.lcd.backlight(value)
        return {"backlight": value}

    async def set_line1(self, text: str) -> dict:
        """Put text on the first line"""
        self.lcd.put_line(0, text[:16])
        return {"line1": text}

    async def set_line2(self, text: str) -> dict:
        """Put text on the second line"""
        self.lcd.put_line(1, text[:16])
        return {"line2": text}

    async def stop(self):
        """Stop the LCD"""
        self.lcd.close()


class RGBLight:
    """The RGBLight item"""
    cfg: dict
    mode: str
    gpio: pigpio.pi

    async def init(self):
        """Initialise RGBLight"""
        self.gpio = self.cfg["pigpio_adapter"].pigpio
        with suppress(pigpio.error):  # Pins not used for PWM
            await self.states.set(
                "color",
                Color.from_rgb(
                    (self.gpio.get_PWM_dutycycle(pin)
                     for pin in (
                         self.cfg["pin_r"],
                         self.cfg["pin_g"],
                         self.cfg["pin_b"]))))
        await self.apply_color()

    async def set_color(self, color: Color) -> dict:
        """Setter for color"""
        await self.apply_color(color)
        if await self.states.get("on") != bool(color.l):
            await self.states.update("on", bool(color.l))
        return {"color": color}

    async def apply_color(self, color: Color = None) -> Color:
        """Applies the color without manipulating the state"""
        color = color or await self.states.get("color")
        color_tup = color.rgb
        for pin, val in (
                (self.cfg["pin_r"], color_tup[0]),
                (self.cfg["pin_g"], color_tup[1]),
                (self.cfg["pin_b"], color_tup[2])):
            self.gpio.set_PWM_dutycycle(pin, val)
        return color

    async def set_mode(self, mode: str) -> dict:
        """Set a mode"""
        if mode == "static":
            return {"mode": mode, "color": await self.apply_color()}
        return {"mode": mode}

    async def set_on(self, value: bool) -> dict:
        """Setter for on"""
        if value:
            if not await self.states.get("on"):
                return {"on": True, "color": await self.apply_color()}
            return {}

        await self.apply_color(Color(0, 0, 0))
        return {"on": False}

    async def toggle_on(self):
        """Action: Toggle"""
        await self.set_on(not await self.states.get("on"))

    async def set_hue(self, value):
        """Set Hue"""
        color = await self.states.get("color")
        color.h = value
        await self.states.set("color", color)

    async def set_saturation(self, value):
        """Set Saturation"""
        color = await self.states.get("color")
        color.s = value
        await self.states.set("color", color)

    async def set_brightness(self, value):
        """Set Brightness"""
        color = await self.states.get("color")
        color.l = value
        await self.states.set("color", color)

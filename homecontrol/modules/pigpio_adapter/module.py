from contextlib import suppress
from dependencies.lcd import LCD
import asyncio
from dependencies.throttle_function import throttle
from core import Core
import pigpio


class Module:
    core: Core
    meta: dict

    async def init(self):
        return

    async def stop(self):
        return


class PiGPIOAdapter:
    cfg: dict
    pigpio: pigpio.pi
    core: Core

    async def init(self):
        done, pending = await asyncio.wait({self.core.loop.run_in_executor(None, self.init_pigpio)}, timeout=2)
        if pending:
            return False
        

    def init_pigpio(self):
        self.pigpio = pigpio.pi(self.cfg["host"], self.cfg["port"])

    async def stop(self):
        await asyncio.gather(*self.core.event_engine.broadcast("pigpio_closing", pigpio=self.pigpio))
        self.pigpio.stop()


class BinarySwitch:
    cfg: dict
    core: Core

    async def init(self):
        self.pigpio: pigpio.pi = self.cfg["pigpio_adapter"].pigpio
        self.pigpio.set_mode(self.cfg["pin"], 1)
        self.pigpio.write(self.cfg["pin"], not (await self.states.get("on")) ^ self.cfg["on_state"])

    async def set_on(self, value: bool) -> dict:
        self.pigpio.write(self.cfg["pin"], not value^self.cfg["on_state"])

        return {"on": value}

    async def toggle_on(self):
        return await self.states.set("on", not await self.states.get("on"))


class Button:
    cfg: dict
    core: Core

    async def init(self):
        self.pigpio: pigpio.pi = self.cfg["pigpio_adapter"].pigpio
        self.pigpio.set_mode(self.cfg["pin"], pigpio.INPUT)
        self.cb = self.pigpio.callback(self.cfg["pin"], pigpio.EITHER_EDGE, self.callback)

    @throttle(s=0.05)
    def callback(self, pin, reading, timestamp) -> None:
        async def _async_callback() -> bool:
            if not self.cfg["toggle"]:
                value = not self.cfg["pull_up"]^reading
                if not value == await self.states.get("value"):
                    await self.states.update("value", value)
                    return True
            else:
                if not self.cfg["pull_up"]^reading:
                    await self.states.update("value", not await self.states.get("value"))
                    return True

        asyncio.run_coroutine_threadsafe(_async_callback(), loop=self.core.loop)

    async def stop(self):
        with suppress(AttributeError, ConnectionResetError):  # pigpio socket already closed
            self.cb.cancel()


class I2CLCD:
    async def init(self):
        self.pigpio: pigpio.pi = self.cfg["pigpio_adapter"].pigpio
        self.lcd = LCD(pi=self.pigpio, bus=self.cfg["bus"], addr=self.cfg["address"],
                       backlight_on=await self.states.get("backlight"))

    async def set_backlight(self, value: bool) -> dict:
        self.lcd.backlight(value)
        return {"backlight": value}

    async def set_line1(self, text: str) -> dict:
        self.lcd.put_line(0, text[:16])
        return {"line1": text}

    async def set_line2(self, text: str) -> dict:
        self.lcd.put_line(1, text[:16])
        return {"line2": text}

    async def stop(self):
        self.lcd.close()
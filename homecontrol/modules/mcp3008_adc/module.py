import logging


LOGGER = logging.getLogger(__name__)


class MCP3008ADC:
    handle = None

    async def init(self) -> bool:
        self.handle = self.cfg["pigpio_adapter"].pigpio.spi_open(
            spi_channel=self.cfg["spi_channel"],
            baud=self.cfg["baud_rate"],
            spi_flags=self.cfg["spi_flags"]
        )

    def get_value(self, channel: int) -> int:
        adc = self.cfg["pigpio_adapter"].pigpio.spi_xfer(self.handle, [1, (8 + channel) << 4, 0])[1]
        return ((adc[1] & 3) << 8) + adc[2]


    async def stop(self):
        if self.handle is not None:
            try:
                self.cfg["pigpio_adapter"].pigpio.spi_close(self.handle)
            except BrokenPipeError:
                LOGGER.warning(f"SPI transport not properly closed for {self.identifier}")


class AnalogInput:
    async def init(self):
        self.adc = self.cfg["adc"]
        self.raw_val = 0
        tick(self.cfg["update_interval"])(self.poll_value)

    async def get_value(self):
        return self.adc.get_value(self.cfg["channel"])

    async def poll_value(self):
        new_raw_val = await self.get_value()
        if abs(self.raw_val - new_raw_val) >= self.cfg["change_threshold"]:
            await self.update_raw(new_raw_val)

    async def update_raw(self, raw_val):
        self.raw_val = raw_val
        await self.states.update("value", self.value(raw_val))

    def value(self, raw_val) -> int:
        return int(self.cfg["min"]+raw_val*(self.cfg["max"]-self.cfg["min"])/1023+0.5)

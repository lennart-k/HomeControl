"""Supports the MCP3008 ADC using PiGPIO"""

import logging

from homecontrol.dependencies.entity_types import Item


LOGGER = logging.getLogger(__name__)


class MCP3008ADC(Item):
    """The MCP3008ADC item"""
    handle = None

    async def init(self) -> bool:
        """Initialise the item"""
        self.handle = self.cfg["pigpio_adapter"].pigpio.spi_open(
            spi_channel=self.cfg["spi_channel"],
            baud=self.cfg["baud_rate"],
            spi_flags=self.cfg["spi_flags"]
        )

    def get_value(self, channel: int) -> int:
        """Get the value for one channel"""
        adc = self.cfg["pigpio_adapter"].pigpio.spi_xfer(
            self.handle, [1, (8 + channel) << 4, 0])[1]
        return ((adc[1] & 3) << 8) + adc[2]

    async def stop(self):
        """Stop the item"""
        if self.handle is not None:
            try:
                self.cfg["pigpio_adapter"].pigpio.spi_close(self.handle)
            except BrokenPipeError:
                LOGGER.warning("SPI transport not properly closed for %s",
                               self.identifier)


class AnalogInput(Item):
    """Item that holds an analog reading"""
    async def init(self):
        """Initialise the item"""
        self.adc = self.cfg["adc"]
        self.raw_value = 0

    async def get_value(self) -> int:
        """Getter for the value"""
        new_raw_value = self.adc.get_value(self.cfg["channel"])
        if abs(self.raw_value - new_raw_value) >= self.cfg["change_threshold"]:
            self.raw_value = new_raw_value
        return self.value(self.raw_value)

    def value(self, raw_val) -> int:
        """
        Translate the raw reading
        to a range defined in the item's configuration
        """
        return int(
            self.cfg["min"]
            + raw_val * (self.cfg["max"]
                         - self.cfg["min"]) / 1023
            + 0.5)

"""Supports the MCP3008 ADC using PiGPIO"""

import logging

import voluptuous as vol
from homecontrol.const import ItemStatus
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_proxy import StateDef

SPEC = {
    "name": "MCP3008",
    "description": "Support for the MCP3008 ADC which "
                   "enables the Raspberry Pi to get analog input"
}

LOGGER = logging.getLogger(__name__)


class MCP3008ADC(Item):
    """The MCP3008ADC item"""
    handle = None
    config_schema = vol.Schema({
        vol.Required("pigpio_adapter"): str,
        vol.Required("spi_channel", default=0): vol.All(
            int, vol.Range(0, 2)),
        vol.Required("baud_rate"): int,
        vol.Required("spi_flags", default=0): int
    }, extra=vol.ALLOW_EXTRA)

    async def init(self) -> bool:
        """Initialise the item"""
        self.pigpio_adapter = self.core.item_manager.get_item(
            self.cfg["pigpio_adapter"])

        if not self.pigpio_adapter:
            return ItemStatus.WAITING_FOR_DEPENDENCY

        self.handle = self.cfg["pigpio_adapter"].pigpio.spi_open(
            spi_channel=self.cfg["spi_channel"],
            baud=self.cfg["baud_rate"],
            spi_flags=self.cfg["spi_flags"]
        )

    def get_value(self, channel: int) -> int:
        """Get the value for one channel"""
        adc = self.pigpio_adapter.pigpio.spi_xfer(
            self.handle, [1, (8 + channel) << 4, 0])[1]
        return ((adc[1] & 3) << 8) + adc[2]

    async def stop(self):
        """Stop the item"""
        if self.handle is not None:
            try:
                self.pigpio_adapter.pigpio.spi_close(self.handle)
            except BrokenPipeError:
                LOGGER.warning("SPI transport not properly closed for %s",
                               self.identifier)


class AnalogInput(Item):
    """Item that holds an analog reading"""
    config_schema = vol.Schema({
        vol.Required("adc"): str,
        vol.Required("channel", default=0): vol.All(
            int, vol.Range(0, 7)),
        vol.Required("min", default=0): int,
        vol.Required("max", default=1023): int,
        vol.Required("change_threshold", default=0): vol.All(
            int, vol.Range(0))
    }, extra=vol.ALLOW_EXTRA)

    value = StateDef(default=0, poll_interval=0.1)

    async def init(self):
        """Initialise the item"""
        self.adc = self.core.item_manager.get_item(self.cfg["adc"])
        if not self.adc:
            return ItemStatus.WAITING_FOR_DEPENDENCY
        self.raw_value = 0

    @value.getter()
    async def get_value(self) -> int:
        """Getter for the value"""
        new_raw_value = self.adc.get_value(self.cfg["channel"])
        if abs(self.raw_value - new_raw_value) >= self.cfg["change_threshold"]:
            self.raw_value = new_raw_value
        return self.translate_value(self.raw_value)

    def translate_value(self, raw_val) -> int:
        """
        Translate the raw reading
        to a range defined in the item's configuration
        """
        return int(
            self.cfg["min"]
            + raw_val * (self.cfg["max"]
                         - self.cfg["min"]) / 1023
            + 0.5)

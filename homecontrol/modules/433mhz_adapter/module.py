"""Support for 3-pin 433MHz receivers and transmitters using pigpio"""

# pylint: disable=import-error
import voluptuous as vol
from homecontrol.dependencies.entity_types import Item

from .dependencies import rf


class RFRXAdapter(Item):
    """The RX adapter"""
    config_schema = vol.Schema({
        vol.Required("pin", default=20): vol.All(
            vol.Coerce(int), vol.Range(2, 40)),
        vol.Required("pigpio_adapter"): str
    }, extra=vol.ALLOW_EXTRA)

    # pylint: disable=invalid-name
    async def init(self):
        """Initialise the RX adapter"""
        self.rx = rf.RX(
            self.cfg["pigpio_adapter"].pigpio,
            gpio=self.cfg["pin"],
            callback=self._callback_helper,
            max_bits=12)

    # pylint: disable=invalid-name
    def _callback_helper(self, code, length, gap, t0, t1):
        self.core.event_bus.broadcast(
            "rf_code_received", code=code, length=length)

    async def stop(self):
        """Stop the receiver"""
        self.rx.cancel()


class RFTXAdapter(Item):
    """The TX adapter"""
    config_schema = vol.Schema({
        vol.Required("pin", default=20): vol.All(
            vol.Coerce(int), vol.Range(2, 40)),
        vol.Required("pigpio_adapter"): str,
        vol.Required("bits", default=12): vol.Coerce(int)
    }, extra=vol.ALLOW_EXTRA)

    # pylint: disable=invalid-name
    async def init(self):
        """Initialise the TX adapter"""
        self.tx = rf.TX(self.cfg["pigpio_adapter"].pigpio,
                        gpio=self.cfg["pin"], bits=self.cfg["bits"])

    async def send_code(self, code):
        """Send a code"""
        await self.tx.send(code)

    async def stop(self):
        """Stop the transmitter"""
        self.tx.cancel()

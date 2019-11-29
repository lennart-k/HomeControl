"""Support for 3-pin 433MHz receivers and transmitters using pigpio"""

# pylint: disable=import-error
from .dependencies import rf

from homecontrol.dependencies.entity_types import Item

class RFRXAdapter(Item):
    """The RX adapter"""
    cfg: dict

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
        self.core.event_engine.broadcast(
            "rf_code_received", code=code, length=length)

    async def stop(self):
        """Stop the receiver"""
        self.rx.cancel()


class RFTXAdapter(Item):
    """The TX adapter"""
    cfg: dict

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

"""Module providing an IR receiver"""

# pylint: disable=import-error
import voluptuous as vol
from homecontrol.dependencies.entity_types import Item
from .dependencies.ir_receiver import NECIRReceiver as Receiver
from homecontrol.const import ItemStatus


class NECIRReceiver(Item):
    """The receiver item"""
    config_schema = vol.Schema({
        vol.Required("pin", default=16): vol.All(
            vol.Coerce(int), vol.Range(2, 40)),
        vol.Required("pigpio_adapter"): str
    }, extra=vol.ALLOW_EXTRA)

    async def init(self):
        """Initialise the receiver"""
        self.pigpio_adapter = self.core.item_manager.get(
            self.cfg["pigpio_adapter"])

        if not self.pigpio_adapter:
            return ItemStatus.WAITING_FOR_DEPENDENCY

        self.ir_receiver = Receiver(
            self.pigpio_adapter.pigpio,
            self.cfg["pin"],
            self.on_code,
            10)

    def on_code(self, address, data, bits):
        """Handler for new code"""
        if address and data:
            self.core.event_engine.broadcast(
                "ir_nec_code", address=address, data={"data": data}, bits=bits)

    async def stop(self):
        """Stops the receiver"""
        self.ir_receiver.stop()

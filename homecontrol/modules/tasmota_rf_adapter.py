"""Support for Tasmota RF devices"""

from contextlib import suppress
import json
from functools import reduce
import asyncio
import voluptuous as vol

from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.state_engine import StateDef
from homecontrol.dependencies.action_engine import action

SPEC = {
    "name": "Tasmota RF Adapter",
    "description": "An adapter to transceive 433MHz signals "
                   "using an MQTT device with Tasmota"
}


class TasmotaRFAdapter(Item):
    """The TasmotaRFAdapter class"""
    sending: asyncio.Event
    config_schema = vol.Schema({
        vol.Required("mqtt_adapter"): str,
        vol.Required("topic"): str,
        vol.Required("tx_interval", default=0.5): vol.All(
            vol.Coerce(float), vol.Range(0))
    }, extra=vol.ALLOW_EXTRA)

    async def init(self):
        """Initialise the adapter"""
        self.sending = asyncio.Event()
        self.sending.set()

        @self.core.event_engine.register("mqtt_connected")
        async def on_mqtt_connected(event, mqtt_adapter):
            """Handle connection"""
            if mqtt_adapter == self.cfg["mqtt_adapter"]:
                self.cfg["mqtt_adapter"].client.subscribe(
                    self.cfg["topic"] + "/tele/RESULT")

        @self.core.event_engine.register("mqtt_message_received")
        async def on_mqtt_message_received(event, mqtt_adapter, message):
            """Handle message"""
            if mqtt_adapter == self.cfg["mqtt_adapter"]:
                # pylint: disable=no-member
                with suppress(json.decoder.JSONDecodeError):
                    data = json.loads(message.payload)
                    if data.get("RfReceived"):
                        code = data["RfReceived"].get("Data", 0)
                        bits = bin(int(code, 16))[2:][::2]
                        self.core.event_engine.broadcast(
                            "rf_code_received",
                            code=int(bits, 2),
                            length=len(bits))

    @action("send_code")
    async def send_code(self, code: int) -> None:
        """Send RF code"""
        await self.sending.wait()
        self.sending.clear()
        binary = bin(int(code))[2:]
        zero_padded = reduce(
            lambda x, y: x + y, zip(["0"] * len(binary), binary))
        data = "#" + hex(int("".join(zero_padded), 2))[2:]
        self.cfg["mqtt_adapter"].client.publish(
            self.cfg["topic"] + "/cmnd/RfCode", data)
        self.core.loop.call_later(self.cfg["tx_interval"], self.sending.set)

    async def stop(self):
        """Stops the adapter"""
        self.cfg["mqtt_adapter"].client.unsubscribe(
            self.cfg["topic"] + "/tele/RESULT")

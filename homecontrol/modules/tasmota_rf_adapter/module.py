import json
from functools import reduce


class TasmotaRFAdapter:
    async def init(self):
        @event("mqtt_connected")
        async def on_mqtt_connected(event, adapter):
            if adapter == self.cfg["mqtt_adapter"]:
                self.cfg["mqtt_adapter"].client.subscribe(self.cfg["topic"]+"/tele/RESULT")

        @event("mqtt_message_received")
        async def on_mqtt_message_received(event, adapter, msg):
            if adapter == self.cfg["mqtt_adapter"]:
                try:
                    data = json.loads(msg.payload)
                    if data.get("RfReceived"):
                        code = data["RfReceived"].get("Data", 0)
                        bits = bin(int(code, 16))[2:][::2]
                        self.core.event_engine.broadcast("rf_code_received", code=int(bits, 2), length=len(bits))
                except json.decoder.JSONDecodeError:
                    pass

    async def send_code(self, code):
        binary = bin(int(code))[2:]
        data = "#"+hex(int("".join(reduce(lambda x, y: x+y, zip(["0"]*len(binary), binary))), 2))[2:]
        self.cfg["mqtt_adapter"].client.publish(self.cfg["topic"]+"/cmnd/RfCode", data)

    async def stop(self):
        self.cfg["mqtt_adapter"].client.unsubscribe(self.cfg["topic"]+"/tele/RESULT")

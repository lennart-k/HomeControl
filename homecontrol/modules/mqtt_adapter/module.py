import time
import json
import paho.mqtt.client as mqtt


class MQTTAdapter:
    async def init(self):
        self.client = mqtt.Client()
        self.client.connect_async(self.cfg["host"], self.cfg["port"])
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.loop_start()

    async def stop(self):
        self.client.loop_stop(True)

    def on_connect(self, _, userdata, flags, result):
        self.core.event_engine.broadcast("mqtt_connected", self)

    def on_message(self, _, userdata, msg):
        self.core.event_engine.broadcast("mqtt_message_received", self, msg)

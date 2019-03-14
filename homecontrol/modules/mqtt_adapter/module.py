import asyncio
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
        # Workaround: Without create_task paho-mqtt would cause a RuntimeWarning and interpret it as an exception
        async def do():
            self.core.event_engine.broadcast("mqtt_connected", mqtt_adapter=self)
        self.core.loop.create_task(do())

    def on_message(self, _, userdata, msg):
        # Workaround: Without create_task paho-mqtt would cause a RuntimeWarning and interpret it as an exception
        async def do():
            self.core.event_engine.broadcast("mqtt_message_received", mqtt_adapter=self, message=msg)
        self.core.loop.create_task(do())

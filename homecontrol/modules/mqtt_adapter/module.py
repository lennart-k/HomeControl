"""Module for an MQTT adapter"""

import paho.mqtt.client as mqtt


class MQTTAdapter:
    """The MQTT adapter"""
    async def init(self):
        """Initialise the adapter"""
        self.client = mqtt.Client()
        self.client.connect_async(self.cfg["host"], self.cfg["port"])
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.loop_start()

    async def stop(self):
        """Stop the mqtt session"""
        self.client.loop_stop(True)

    def on_connect(self, _, userdata, flags, result):
        """Handle a connection"""
        self.core.event_engine.broadcast_threaded("mqtt_connected", mqtt_adapter=self)

    def on_message(self, _, userdata, msg):
        """Handle a message"""
        self.core.event_engine.broadcast_threaded("mqtt_message_received",
                                                  mqtt_adapter=self, message=msg)

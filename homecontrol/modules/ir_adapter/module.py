from dependencies.ir_receiver import NECIRReceiver as Receiver


class NECIRReceiver:  # TODO More protocols:
    async def init(self):
        self.ir_receiver = Receiver(self.cfg["pigpio_adapter"].pigpio, self.cfg["pin"], self.on_code, 10)

    def on_code(self, address, data, bits):
        if address and data:
            self.core.event_engine.broadcast("ir_nec_code", address, data, bits)

    async def stop(self):
        self.ir_receiver.stop()

from dependencies import rf


class Module:
    pass


class RFRXAdapter:
    cfg: dict

    async def init(self):
        self.rx = rf.RX(self.cfg["pigpio_adapter"].pigpio,
                        gpio=self.cfg["pin"], callback=self.callback_helper, max_bits=12)

    def callback_helper(self, code, length, gap, t0, t1):
        self.core.event_engine.broadcast(
            "rf_code_received", code=code, length=length)

    async def stop(self):
        self.rx.cancel()


class RFTXAdapter:
    cfg: dict

    async def init(self):
        self.tx = rf.TX(self.cfg["pigpio_adapter"].pigpio,
                        gpio=self.cfg["pin"], bits=self.cfg["bits"])

    async def send_code(self, code):
        await self.tx.send(code)

    async def stop(self):
        self.tx.cancel()

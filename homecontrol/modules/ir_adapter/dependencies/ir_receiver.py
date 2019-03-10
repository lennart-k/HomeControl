from functools import reduce
import math
import pigpio

PULSE_LENGTH = 562.5  # https://techdocs.altium.com/display/FPGA/NEC+Infrared+Transmission+Protocol
HALF_PULSE_LENGTH = PULSE_LENGTH/2

LEADING_BURST = 16


class NECIRReceiver:  # TODO Repeat codes
    def __init__(self, pi, gpio, callback, timeout=5):
        self.pi = pi
        self.gpio = gpio
        self.code_timeout = timeout
        self.callback = callback
        self.started = False
        self.edges = []
        self.last_tick = 0

        pi.set_mode(gpio, pigpio.INPUT)

        self.cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cb)
        self.pi.set_watchdog(self.gpio, self.code_timeout)

    def _cb(self, gpio, level, tick):
        if not level == pigpio.TIMEOUT:
            if not self.started:
                self.started = True
                self.edges = []
            if self.last_tick:
                self.edges.append(tick - self.last_tick)
            self.last_tick = tick

        else:
            if self.started:
                self.started = False
                self.last_tick = 0
                if len(self.edges) > 12:
                    self.on_packet(self.edges)

    def _bits_to_int(self, bits):
        out = 0
        for bit in bits:
            out = (out << 1) | bit
        return out

    def on_packet(self, edges):
        pulse_edges = list(map(lambda x: math.floor((x + HALF_PULSE_LENGTH) / PULSE_LENGTH), edges))
        if pulse_edges.pop(0) == 16:  # Leading pulse
            if pulse_edges.pop(0) == 8:  # 8 unit space
                if reduce(lambda x, y: 1 if x == y else 0, pulse_edges[::2]):
                    bits = [0 if bit == 1 else 1 for bit in pulse_edges[1::2]]
                    address = self._bits_to_int(bits[:8])
                    for bit, inverse in zip(bits[:8], bits[8:16]):
                        if not bit + inverse == 1:
                            address = None
                    data = self._bits_to_int(bits[16:24])
                    for bit, inverse in zip(bits[16:24], bits[24:32]):
                        if not bit + inverse == 1:
                            data = None

                    self.callback(address, data, bits)

    def stop(self):
        self.cb.cancel()
        self.pi.set_watchdog(self.gpio, 0)


if __name__ == "__main__":
    import time

    def callback(address, data, bits):
        print(address, " - ", data, " - ", bits)


    pi = pigpio.pi()

    ir = NECIRReceiver(pi, 16, callback, 10)

    time.sleep(30000)

    pi.stop()

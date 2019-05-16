"""Module providing an NEC IR code receiver"""

from functools import reduce
import math
import pigpio

# https://techdocs.altium.com/display/FPGA/NEC+Infrared+Transmission+Protocol
PULSE_LENGTH = 562.5
HALF_PULSE_LENGTH = PULSE_LENGTH/2

LEADING_BURST = 16


class NECIRReceiver:
    """Receives IR codes using the NEC protocol"""

    # pylint: disable=invalid-name
    def __init__(self, rpi: pigpio.pi, gpio: int, callback: callable, timeout: int = 5):
        self.pi = rpi
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

    # pylint: disable=no-self-use
    def _bits_to_int(self, bits):
        out = 0
        for bit in bits:
            out = (out << 1) | bit
        return out

    def on_packet(self, edges):
        """Handles a packet"""
        pulse_edges = list(map(lambda x: math.floor(
            (x + HALF_PULSE_LENGTH) / PULSE_LENGTH), edges))
        if pulse_edges.pop(0) != 16:  # Leading pulse
            return
        if pulse_edges.pop(0) != 8:  # 8 unit space
            return
        if not reduce(lambda x, y: 1 if x == y else 0, pulse_edges[::2]):
            return
        bits = [0 if bit == 1 else 1 for bit in pulse_edges[1::2]]
        address = self._bits_to_int(bits[:8])
        for bit, inverse in zip(bits[:8], bits[8:16]):
            if bit + inverse != 1:
                address = None
        data = self._bits_to_int(bits[16:24])
        for bit, inverse in zip(bits[16:24], bits[24:32]):
            if bit + inverse != 1:
                data = None

            self.callback(address, data, bits)

    def stop(self):
        """Stop listening"""
        self.cb.cancel()
        self.pi.set_watchdog(self.gpio, 0)


if __name__ == "__main__":
    # pylint: disable=invalid-name

    import time

    def _callback(address, data, bits):
        print(address, " - ", data, " - ", bits)

    pi = pigpio.pi()

    ir = NECIRReceiver(pi, 16, _callback, 10)

    time.sleep(30000)

    pi.stop()

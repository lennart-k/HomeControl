"""Support for simple 3-pin 433MHz receivers and transmitters"""

import asyncio
import pigpio

# pylint: disable=invalid-name,too-many-instance-attributes


class RX:
    """Receiver"""

    _lt_0: int
    _lt_1: int
    _min_0: int
    _min_1: int
    _max_0: int
    _max_1: int
    _lbits: int
    _lcode: int
    _lgap: int
    _bits: int
    _t_0: int
    _t_1: int
    _e0: int
    _even_edge_len: int

    def __init__(self, pi: pigpio.pi, gpio, callback=None,
                 min_bits=8, max_bits=12, glitch=150):
        self.pi = pi
        self.gpio = gpio
        self.cb = callback
        self.min_bits = min_bits * 2
        self.max_bits = max_bits * 2
        self.glitch = glitch

        self._in_code = False
        self._edge = 0
        self._code = 0
        self._gap = 0

        self._ready = False

        pi.set_mode(gpio, pigpio.INPUT)
        pi.set_glitch_filter(gpio, glitch)

        self._last_edge_tick = pi.get_current_tick()
        self._cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cbf)

    def _timings(self, e0, e1):
        if e0 < e1:
            shorter = e0
            longer = e1
        else:
            shorter = e1
            longer = e0

        if self._bits:
            self._t_0 += shorter
            self._t_1 += longer
        else:
            self._t_0 = shorter
            self._t_1 = longer

        self._bits += 1

    def _calibrate(self, e0, e1):
        self._bits = 0
        self._timings(e0, e1)
        self._bits = 0

        ratio = float(self._t_1) / float(self._t_0)

        if ratio < 1.5:
            self._in_code = False

        slack0 = int(0.3 * self._t_0)
        slack1 = int(0.2 * self._t_1)

        self._min_0 = self._t_0 - slack0
        self._max_0 = self._t_0 + slack0
        self._min_1 = self._t_1 - slack1
        self._max_1 = self._t_1 + slack1

    def _test_bit(self, e0, e1):
        self._timings(e0, e1)

        if ((self._min_0 < e0 < self._max_0)
                and (self._min_1 < e1 < self._max_1)):
            return 0
        if ((self._min_0 < e1 < self._max_0)
                and (self._min_1 < e0 < self._max_1)):
            return 1
        return 2

    def _cbf(self, g, l, t):
        edge_len = pigpio.tickDiff(self._last_edge_tick, t)
        self._last_edge_tick = t
        if edge_len > 5000:
            if self._in_code:
                if self.min_bits <= self._bits <= self.max_bits:
                    self._lbits = self._bits
                    self._lcode = self._code
                    self._lgap = self._gap
                    self._lt_0 = int(self._t_0 / self._bits)
                    self._lt_1 = int(self._t_1 / self._bits)
                    self._ready = True
                    if self.cb is not None:
                        self.cb(int(bin(self._lcode)[2::2], 2),
                                int(self._lbits / 2),
                                self._lgap, self._lt_0, self._lt_1)
            self._in_code = True
            self._gap = edge_len
            self._edge = 0
            self._bits = 0
            self._code = 0
        elif self._in_code:
            if self._edge == 0:
                self._e0 = edge_len
            elif self._edge == 1:
                self._calibrate(self._e0, edge_len)
            if self._edge % 2:
                bit = self._test_bit(self._even_edge_len, edge_len)
                self._code = self._code << 1
                if bit == 1:
                    self._code += 1
                elif bit != 0:
                    self._in_code = False
            else:
                self._even_edge_len = edge_len
            self._edge += 1

    def ready(self):
        """Returns if RX is ready"""
        return self._ready

    def cancel(self):
        """Stop listening"""
        if self._cb is not None:
            if self.pi.sl.s:
                # Remove glitch filter.
                self.pi.set_glitch_filter(self.gpio, 0)
                self._cb.cancel()
                self._cb = None


class TX:
    """Transmitter"""

    def __init__(self,
                 pi: pigpio.pi,
                 gpio: int,
                 repeats: int = 6,
                 bits: int = 12,
                 gap: int = 9000,
                 t_0: int = 300,
                 t_1: int = 900) -> None:
        self.pi = pi
        self.gpio = gpio
        self.repeats = repeats
        self.bits = bits
        self.gap = gap
        self.t_0 = t_0
        self.t_1 = t_1

        self._make_waves()

        pi.set_mode(gpio, pigpio.OUTPUT)

    def _make_waves(self):
        wf = [pigpio.pulse(1 << self.gpio, 0, self.t_0),
              pigpio.pulse(0, 1 << self.gpio, self.gap)]
        self.pi.wave_add_generic(wf)
        self._amble = self.pi.wave_create()

        wf = [pigpio.pulse(1 << self.gpio, 0, self.t_0),
              pigpio.pulse(0, 1 << self.gpio, self.t_1)]
        self.pi.wave_add_generic(wf)
        self._wid0 = self.pi.wave_create()

        wf = [pigpio.pulse(1 << self.gpio, 0, self.t_1),
              pigpio.pulse(0, 1 << self.gpio, self.t_0)]
        self.pi.wave_add_generic(wf)
        self._wid1 = self.pi.wave_create()

    def set_repeats(self, repeats):
        """Sets the number of repeats"""
        if 1 < repeats < 100:
            self.repeats = repeats

    def set_bits(self, bits):
        """Sets the bits to send"""
        if 5 < bits < 65:
            self.bits = bits

    def set_timings(self, gap, t_0, t_1):
        """Sets the timings"""
        self.gap = gap
        self.t_0 = t_0
        self.t_1 = t_1

        self.pi.wave_delete(self._amble)
        self.pi.wave_delete(self._wid0)
        self.pi.wave_delete(self._wid1)

        self._make_waves()

    async def send(self, code):
        """Sends a code"""
        chain = [self._amble, 255, 0]

        bit = (1 << (self.bits - 1))
        for _ in range(self.bits):
            if code & bit:
                chain += [self._wid0, self._wid1]
            else:
                chain += [self._wid0, self._wid0]
            bit >>= 1

        chain += [self._amble, 255, 1, self.repeats, 0]

        self.pi.wave_chain(chain)

        while self.pi.wave_tx_busy():
            await asyncio.sleep(0.1)

    def cancel(self):
        """Cancels the transfer"""
        if self.pi.sl.s:
            self.pi.wave_delete(self._amble)
            self.pi.wave_delete(self._wid0)
            self.pi.wave_delete(self._wid1)


if __name__ == "__main__":
    import time

    RX_PIN = 20
    TX_PIN = 21

    def _rx_callback(code, bits, gap, t_0, t_1):
        print("code={} bits={} (gap={} t_0={} t_1={})".
              format(code, bits, gap, t_0, t_1))

    rpi = pigpio.pi()  # Connect to local Pi.

    rx = RX(rpi, gpio=RX_PIN, callback=_rx_callback)

    time.sleep(60)

    rx.cancel()

    rpi.stop()

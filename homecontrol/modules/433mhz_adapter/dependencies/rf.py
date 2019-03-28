import asyncio
import pigpio


class RX:
    def __init__(self, pi: pigpio.pi, gpio, callback=None,
                 min_bits=8, max_bits=12, glitch=150):
        self.pi = pi
        self.gpio = gpio
        self.cb = callback
        self.min_bits = min_bits*2
        self.max_bits = max_bits*2
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
            self._t0 += shorter
            self._t1 += longer
        else:
            self._t0 = shorter
            self._t1 = longer

        self._bits += 1

    def _calibrate(self, e0, e1):
        self._bits = 0
        self._timings(e0, e1)
        self._bits = 0

        ratio = float(self._t1) / float(self._t0)

        if ratio < 1.5:
            self._in_code = False

        slack0 = int(0.3 * self._t0)
        slack1 = int(0.2 * self._t1)

        self._min_0 = self._t0 - slack0
        self._max_0 = self._t0 + slack0
        self._min_1 = self._t1 - slack1
        self._max_1 = self._t1 + slack1

    def _test_bit(self, e0, e1):
        self._timings(e0, e1)

        if ((self._min_0 < e0 < self._max_0) and
                (self._min_1 < e1 < self._max_1)):
            return 0
        elif ((self._min_0 < e1 < self._max_0) and
              (self._min_1 < e0 < self._max_1)):
            return 1
        else:
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
                    self._lt0 = int(self._t0 / self._bits)
                    self._lt1 = int(self._t1 / self._bits)
                    self._ready = True
                    if self.cb is not None:
                        self.cb(int(bin(self._lcode)[2::2], 2), int(self._lbits/2),
                                self._lgap, self._lt0, self._lt1)
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
        return self._ready

    def code(self):
        self._ready = False
        return self._lcode

    def details(self):
        self._ready = False
        return self._lcode, self._lbits, self._lgap, self._lt0, self._lt1

    def cancel(self):
        if self._cb is not None:
            if self.pi.sl.s:
                self.pi.set_glitch_filter(self.gpio, 0)  # Remove glitch filter.
                self._cb.cancel()
                self._cb = None


class TX:
    def __init__(self, pi, gpio, repeats=6, bits=12, gap=9000, t0=300, t1=900):
        self.pi = pi
        self.gpio = gpio
        self.repeats = repeats
        self.bits = bits
        self.gap = gap
        self.t0 = t0
        self.t1 = t1

        self._make_waves()

        pi.set_mode(gpio, pigpio.OUTPUT)

    def _make_waves(self):
        wf = [pigpio.pulse(1 << self.gpio, 0, self.t0), pigpio.pulse(0, 1 << self.gpio, self.gap)]
        self.pi.wave_add_generic(wf)
        self._amble = self.pi.wave_create()

        wf = [pigpio.pulse(1 << self.gpio, 0, self.t0), pigpio.pulse(0, 1 << self.gpio, self.t1)]
        self.pi.wave_add_generic(wf)
        self._wid0 = self.pi.wave_create()

        wf = [pigpio.pulse(1 << self.gpio, 0, self.t1), pigpio.pulse(0, 1 << self.gpio, self.t0)]
        self.pi.wave_add_generic(wf)
        self._wid1 = self.pi.wave_create()

    def set_repeats(self, repeats):
        if 1 < repeats < 100:
            self.repeats = repeats

    def set_bits(self, bits):
        if 5 < bits < 65:
            self.bits = bits

    def set_timings(self, gap, t0, t1):
        self.gap = gap
        self.t0 = t0
        self.t1 = t1

        self.pi.wave_delete(self._amble)
        self.pi.wave_delete(self._wid0)
        self.pi.wave_delete(self._wid1)

        self._make_waves()

    async def send(self, code):
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
        if self.pi.sl.s:
            self.pi.wave_delete(self._amble)
            self.pi.wave_delete(self._wid0)
            self.pi.wave_delete(self._wid1)


if __name__ == "__main__":
    import time

    RX_PIN = 20
    TX_PIN = 21


    def rx_callback(code, bits, gap, t0, t1):
        print("code={} bits={} (gap={} t0={} t1={})".
              format(code, bits, gap, t0, t1))


    pi = pigpio.pi()  # Connect to local Pi.

    rx = RX(pi, gpio=RX_PIN, callback=rx_callback)

    time.sleep(60)

    rx.cancel()

    pi.stop()

# Rotary encoder KY-040 driven by interrupts
#
#   enc = Encoder(clk=15, dt=14, sw=2)
#   enc.read()      # clicks since the last call (+ right, - left)
#   enc.pressed()   # True if the button was pressed since the last call

from machine import Pin, disable_irq, enable_irq
from time import ticks_ms, ticks_diff

# Transition (old state << 2 | new state) -> -1 / 0 / +1, state = (CLK << 1) | DT
_TABLE = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)


class Encoder:
    def __init__(self, clk, dt, sw, steps_per_click=4, debounce_ms=200):
        self._clk = Pin(clk, Pin.IN, Pin.PULL_UP)
        self._dt = Pin(dt, Pin.IN, Pin.PULL_UP)
        self._sw = Pin(sw, Pin.IN, Pin.PULL_UP)
        self._spc = steps_per_click
        self._debounce = debounce_ms
        self._state = (self._clk() << 1) | self._dt()
        self._acc = 0              # steps towards the next click
        self._delta = 0            # finished clicks
        self._pressed = False
        self._last_press = 0
        edges = Pin.IRQ_FALLING | Pin.IRQ_RISING
        self._clk.irq(self._on_rotate, edges)
        self._dt.irq(self._on_rotate, edges)
        self._sw.irq(self._on_button, Pin.IRQ_FALLING)

    def _on_rotate(self, pin):
        new = (self._clk() << 1) | self._dt()
        self._acc += _TABLE[(self._state << 2) | new]
        self._state = new
        if self._acc >= self._spc:
            self._acc = 0
            self._delta += 1
        elif self._acc <= -self._spc:
            self._acc = 0
            self._delta -= 1

    def _on_button(self, pin):
        now = ticks_ms()
        if ticks_diff(now, self._last_press) > self._debounce:
            self._last_press = now
            self._pressed = True

    def read(self):
        irq = disable_irq()
        d = self._delta
        self._delta = 0
        enable_irq(irq)
        return d

    def pressed(self):
        irq = disable_irq()
        p = self._pressed
        self._pressed = False
        enable_irq(irq)
        return p

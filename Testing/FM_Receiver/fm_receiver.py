from machine import Pin, I2C
import time


# Configuration of pins
SDA = 18
CLK = 19
RST = 6
RPi_I2C_ID = 1
INITIAL_VOLUME = 8
SEEK_RSSI_THRESHOLD = 0x19
MAX_RDS_BLOCK_ERRORS = 1 

# Constants
_ADDR = 0x10

# Power config (register 0x20)
_DMUTE = 0x4000
_MONO = 0x2000 #forces mono output
_SKMODE = 0x0400 
_SEEKUP = 0x0200
_SEEK = 0x0100
_DISABLE = 0x0040
_ENABLE = 0x0001

#Channel settings (register 0x03)
_TUNE = 0x8000

# System Configuration 1 (Register 0x04)
_RDS = 0x1000
_DE = 0x0800

# Status RSSI (register 0x0A)
_RDSR = 0x8000
_STC = 0x4000
_SFBL = 0x2000
_RDSS = 0x0800
_ST = 0x0100

_RTPLUS_AID = 0x4BD7  # Application ID of RadioText Plus
_CT_TITLE = 1
_CT_ARTIST = 4

_i2c = None
_band = _space = _de = 0
_lo = _hi = _step = 0.0


def _read():
    """Read all 16 registers; returns a list indexed by register number."""
    raw = _i2c.readfrom(_ADDR, 32)
    r = [(raw[i] << 8) | raw[i + 1] for i in range(0, 32, 2)]
    return r[6:] + r[:6]          # chip sends 0x0A first, wraps to 0x00

def _write(r):
    """Write registers 0x02..0x07 (the chip always starts writing at 0x02)."""
    buf = bytearray(12)
    for n in range(6):
        v = r[2 + n]
        buf[2 * n] = v >> 8
        buf[2 * n + 1] = v & 0xFF
    _i2c.writeto(_ADDR, buf)

def _wait_stc(want_set, timeout_ms):
    """Wait until the STC flag equals want_set; returns reg 0x0A."""
    t0 = time.ticks_ms()
    while True:
        s = _read()[0x0A]
        if bool(s & _STC) == want_set:
            return s
        if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
            raise OSError("Si4703: timeout waiting for STC")
        time.sleep_ms(10)

def _reset_into_i2c():
    """SDIO low while RST rises (with SEN high) selects 2-wire mode."""
    global _i2c
    Pin(SDA, Pin.OUT, value=0)
    rst = Pin(RST, Pin.OUT, value=0)
    time.sleep_ms(10)
    rst.value(1)
    time.sleep_ms(10)
    _i2c = I2C(RPi_I2C_ID, sda=Pin(SDA), scl=Pin(CLK), freq=100000)


def init():
    #(Re)initialise the chip. Called automatically on import.
    global _band, _space, _de, _lo, _hi, _step 
    _band, _space, _de, _lo, _hi, _step = (0, 1, 1, 87.5, 108.0, 0.1)

    _reset_into_i2c()
    if _ADDR not in _i2c.scan():
        raise OSError("Si4703 not found on I2C (check wiring, SEN high)")
    r = _read()
    if r[0x00] != 0x1242:
        raise OSError("Unexpected chip ID 0x%04X" % r[0x00])
 
    r[0x07] = 0x8100                  # XOSCEN: start the crystal oscillator
    _write(r)
    time.sleep_ms(500)
 
    r = _read()
    r[0x02] = _DMUTE | _ENABLE        # power up, unmute
    r[0x04] |= _RDS                   # enable RDS
    if _de:
        r[0x04] |= _DE
    else:
        r[0x04] &= ~_DE
    r[0x05] = (SEEK_RSSI_THRESHOLD << 8) | (_band << 6) | (_space << 4) | \
              (INITIAL_VOLUME & 0xF)
    _write(r)
    time.sleep_ms(110)
    _rds.reset()


def power_down():
    r = _read()
    r[0x02] = _DISABLE | _ENABLE      # both bits set = power down
    _write(r)

def set_freq(mhz, timeout_ms=2000):
    """Tune to a frequency in MHz. Returns the frequency actually tuned."""
    if not (_lo <= mhz <= _hi):
        raise ValueError("%.1f MHz outside %.1f-%.1f" % (mhz, _lo, _hi))
    chan = int(round((mhz - _lo) / _step))
    r = _read()
    r[0x03] = _TUNE | chan
    _write(r)
    _wait_stc(True, timeout_ms)
    r = _read()
    r[0x03] &= ~_TUNE
    _write(r)
    _wait_stc(False, timeout_ms)
    _rds.reset()
    return get_freq()


def get_freq():
    chan = _read()[0x0B] & 0x03FF     # READCHAN
    return round(_lo + chan * _step, 1)


def set_volume(vol):
    """0..15"""
    vol = max(0, min(15, int(vol)))
    r = _read()
    r[0x05] = (r[0x05] & 0xFFF0) | vol
    _write(r)

def get_volume():
    return _read()[0x05] & 0xF

def mute(state=True):
    r = _read()
    r[0x02] = (r[0x02] & ~_DMUTE) if state else (r[0x02] | _DMUTE)
    _write(r)

def set_mono(state=True):
    r = _read()
    r[0x02] = (r[0x02] | _MONO) if state else (r[0x02] & ~_MONO)
    _write(r)

def scan_band(min_rssi=15):
    """Tune across the whole band; returns [(freq, rssi), ...] above min_rssi."""
    found = []
    n = int(round((_hi - _lo) / _step))
    for i in range(n + 1):
        f = round(_lo + i * _step, 1)
        set_freq(f)
        rssi = _read()[0x0A] & 0xFF
        if rssi >= min_rssi:
            found.append((f, rssi))
    return found
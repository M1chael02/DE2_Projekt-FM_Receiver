# Si4703 FM receiver with RDS - Raspberry Pi Pico W, MicroPython
#
#   import fm_receiver as fm
#   fm.set_freq(95.1)       # MHz
#   fm.set_volume(8)        # 0-15
#   fm.update_rds()         # call often (at least every ~40 ms)
#   fm.get_rds()            # {"ps": ..., "rt": ..., "artist": ..., ...}

from machine import Pin, I2C
from struct import pack, unpack
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms

# --- Pins and settings ---
SDA = 18
SCL = 19
RST = 6
I2C_ID = 1
INITIAL_VOLUME = 8
SEEK_RSSI_THRESHOLD = 0x19
MAX_RDS_BLOCK_ERRORS = 1

# --- Chip constants ---
_ADDR = 0x10
_CHIP_ID = 0x1242

# Power config (register 0x02)
_DMUTE = 0x4000          # 1 = unmuted
_MONO = 0x2000           # forces mono output
_DISABLE = 0x0040
_ENABLE = 0x0001

# Channel (register 0x03)
_TUNE = 0x8000

# System config 1 (register 0x04)
_RDS = 0x1000
_DE = 0x0800             # 50 us de-emphasis (Europe)

# Status (register 0x0A)
_RDSR = 0x8000
_STC = 0x4000
_RDSS = 0x0800
_ST = 0x0100

# Band: 87.5-108 MHz (CCIR), 100 kHz step
_BAND = 0 << 6
_SPACE = 1 << 4
_LO = 87.5
_HI = 108.0
_STEP = 0.1

_RTPLUS_AID = 0x4BD7     # application ID of RadioText Plus
_CT_TITLE = 1
_CT_ARTIST = 4

_i2c = None


# --- Low level ---
def _read():
    """Read all 16 registers; returns a list indexed by register number."""
    r = list(unpack(">16H", _i2c.readfrom(_ADDR, 32)))
    return r[6:] + r[:6]          # chip sends 0x0A first, wraps to 0x00

def _read_head(n):
    """Read only the first n registers the chip sends (0x0A, 0x0B, ...)."""
    return unpack(">%dH" % n, _i2c.readfrom(_ADDR, 2 * n))

def _write(r):
    """Write registers 0x02..0x07 (the chip always starts writing at 0x02)."""
    _i2c.writeto(_ADDR, pack(">6H", *r[2:8]))

def _wait_stc(want_set, timeout_ms):
    """Wait until the STC flag equals want_set."""
    t0 = ticks_ms()
    while bool(_read_head(1)[0] & _STC) != want_set:
        if ticks_diff(ticks_ms(), t0) > timeout_ms:
            raise OSError("Si4703: timeout waiting for STC")
        sleep_ms(10)

def _reset_into_i2c():
    """SDIO low while RST rises (with SEN high) selects 2-wire mode."""
    global _i2c
    Pin(SDA, Pin.OUT, value=0)
    rst = Pin(RST, Pin.OUT, value=0)
    sleep_ms(10)
    rst.value(1)
    sleep_ms(10)
    _i2c = I2C(I2C_ID, sda=Pin(SDA), scl=Pin(SCL), freq=100000)

def _chan_to_freq(chan):
    return round(_LO + (chan & 0x03FF) * _STEP, 1)


# --- Control ---
def init():
    """(Re)initialise the chip. Called automatically on import."""
    _reset_into_i2c()
    if _ADDR not in _i2c.scan():
        raise OSError("Si4703 not found on I2C (check wiring, SEN high)")
    r = _read()
    if r[0x00] != _CHIP_ID:
        raise OSError("Unexpected chip ID 0x%04X" % r[0x00])

    r[0x07] = 0x8100                  # XOSCEN: start the crystal oscillator
    _write(r)
    sleep_ms(500)

    r = _read()
    r[0x02] = _DMUTE | _ENABLE        # power up, unmute
    r[0x04] |= _RDS | _DE             # enable RDS and de-emphasis
    r[0x05] = (SEEK_RSSI_THRESHOLD << 8) | _BAND | _SPACE | (INITIAL_VOLUME & 0xF)
    _write(r)
    sleep_ms(110)
    _rds.reset()

def power_down():
    r = _read()
    r[0x02] = _DISABLE | _ENABLE      # both bits set = power down
    _write(r)

def set_freq(mhz, timeout_ms=2000):
    """Tune to a frequency in MHz. Returns the frequency actually tuned."""
    if not (_LO <= mhz <= _HI):
        raise ValueError("%.1f MHz outside %.1f-%.1f" % (mhz, _LO, _HI))
    r = _read()
    r[0x03] = _TUNE | int(round((mhz - _LO) / _STEP))
    _write(r)
    _wait_stc(True, timeout_ms)
    r = _read()
    r[0x03] &= ~_TUNE
    _write(r)
    _wait_stc(False, timeout_ms)
    _rds.reset()
    return get_freq()

def get_freq():
    return _chan_to_freq(_read_head(2)[1])   # READCHAN

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

def get_status():
    r = _read()
    s = r[0x0A]
    return {
        "freq": _chan_to_freq(r[0x0B]),
        "rssi": s & 0xFF,
        "stereo": bool(s & _ST),
        "rds_sync": bool(s & _RDSS),
        "volume": r[0x05] & 0xF,
    }

def scan_band(min_rssi=15):
    """Tune across the whole band; returns [(freq, rssi), ...] above min_rssi."""
    found = []
    n = int(round((_HI - _LO) / _STEP))
    for i in range(n + 1):
        f = round(_LO + i * _STEP, 1)
        set_freq(f)
        rssi = _read_head(1)[0] & 0xFF
        if rssi >= min_rssi:
            found.append((f, rssi))
    return found


# --- RDS ---
def _ch(code):
    """RDS character -> str (printable ASCII only, everything else a space)."""
    return chr(code) if 0x20 <= code < 0x7F else " "


class _RdsDecoder:
    """Accumulates RDS groups into PS name, RadioText and RT+ tags."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.pi = None
        self.pty = None
        self.tp = False
        self.ps = [" "] * 8
        self.ps_mask = 0
        self.rt = [" "] * 64
        self.rt_len = 64
        self.rt_ab = None
        self.rtp_group = None   # group type (5 bits) that carries RT+ tags
        self.rtp_toggle = None
        self.rtp_run = False
        self.tags = {}          # content type -> (start, length)

    def feed(self, a, b, c, d):
        self.pi = a
        self.pty = (b >> 5) & 0x1F
        self.tp = bool(b & 0x0400)
        gtype = b >> 12
        ver_b = (b >> 11) & 1

        if gtype == 0:                          # 0A/0B: Programme Service name
            seg = b & 3
            self.ps[seg * 2] = _ch(d >> 8)
            self.ps[seg * 2 + 1] = _ch(d & 0xFF)
            self.ps_mask |= 1 << seg

        elif gtype == 2:                        # 2A/2B: RadioText
            ab = (b >> 4) & 1
            if ab != self.rt_ab:                # A/B flag toggled: new text
                self.rt_ab = ab
                self.rt = [" "] * 64
                self.rt_len = 64
                self.tags = {}
            seg = b & 0xF
            if ver_b == 0:
                pos = seg * 4
                codes = (c >> 8, c & 0xFF, d >> 8, d & 0xFF)
            else:
                pos = seg * 2
                codes = (d >> 8, d & 0xFF)
            for i, code in enumerate(codes):
                if code == 0x0D:                # carriage return = end of text
                    self.rt_len = pos + i
                    break
                if pos + i < 64:
                    self.rt[pos + i] = _ch(code)

        elif gtype == 3 and ver_b == 0 and c == _RTPLUS_AID:
            # 3A announces that RT+ is sent in group type (b & 0x1F)
            self.rtp_group = b & 0x1F

        elif self.rtp_group is not None and (b >> 11) == self.rtp_group:
            toggle = (b >> 4) & 1               # flips when a new item starts
            if toggle != self.rtp_toggle:
                self.rtp_toggle = toggle
                self.tags = {}
            self.rtp_run = bool(b & 0x08)
            ct1 = ((b & 0x07) << 3) | (c >> 13)
            st1 = (c >> 7) & 0x3F
            ln1 = ((c >> 1) & 0x3F) + 1
            ct2 = ((c & 1) << 5) | (d >> 11)
            st2 = (d >> 5) & 0x3F
            ln2 = (d & 0x1F) + 1
            if ct1:
                self.tags[ct1] = (st1, ln1)
            if ct2:
                self.tags[ct2] = (st2, ln2)

    def ps_text(self):
        return "".join(self.ps).strip() if self.ps_mask == 0xF else ""

    def rt_text(self):
        return "".join(self.rt[:self.rt_len]).strip()

    def tag_text(self, ct):
        t = self.tags.get(ct)
        if not t or not self.rtp_run:
            return None
        txt = "".join(self.rt[t[0]:t[0] + t[1]]).strip()
        return txt or None


_rds = _RdsDecoder()


def update_rds():
    """Poll the chip once. Call at least every ~40 ms.
    Returns True if a new, acceptable RDS group was decoded."""
    s, rb, a, b, c, d = _read_head(6)   # registers 0x0A..0x0F only
    if not (s & _RDSR):
        return False
    errs = max((s >> 9) & 3,            # BLERA
               (rb >> 14) & 3,          # BLERB
               (rb >> 12) & 3,          # BLERC
               (rb >> 10) & 3)          # BLERD
    if errs > MAX_RDS_BLOCK_ERRORS:
        return False
    _rds.feed(a, b, c, d)
    return True

def listen(ms=5000, interval_ms=20):
    """Blocking helper: poll RDS for ms milliseconds."""
    end = ticks_add(ticks_ms(), ms)
    while ticks_diff(end, ticks_ms()) > 0:
        update_rds()
        sleep_ms(interval_ms)

def get_rds():
    """Return what has been decoded so far.

    ps             station name (8 chars), "" until all 4 segments were received
    rt             RadioText (up to 64 chars)
    artist, title  from RT+ tags if the station sends them ("rt+"),
                   otherwise guessed from an "Artist - Title" RadioText ("rt"),
                   otherwise None
    """
    rt = _rds.rt_text()
    artist = _rds.tag_text(_CT_ARTIST)
    title = _rds.tag_text(_CT_TITLE)
    source = "rt+" if (artist or title) else None
    if source is None and " - " in rt:
        a, t = rt.split(" - ", 1)
        artist, title, source = a.strip() or None, t.strip() or None, "rt"
    return {
        "pi": None if _rds.pi is None else "%04X" % _rds.pi,
        "ps": _rds.ps_text(),
        "rt": rt,
        "artist": artist,
        "title": title,
        "source": source,
        "pty": _rds.pty,
    }


init()

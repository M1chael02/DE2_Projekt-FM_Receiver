"""
fm_receiver.py - MicroPython driver for the Si4703 FM tuner (Pololu #1647)
Target: Raspberry Pi Pico W

Importing this module resets the chip into I2C (2-wire) mode, powers it up
and enables RDS. Then use:

    import fm_receiver as fm
    fm.set_freq(95.1)
    fm.set_volume(8)
    fm.listen(5000)          # let RDS data accumulate for 5 s
    print(fm.get_rds())

Register layouts were written from memory of the Si4703 datasheet / AN230.
Check them against the datasheet if something misbehaves.
"""
from machine import Pin, I2C
import time

# ----------------------------------------------------------------- config
SDA_PIN = 18          # Si4703 SDIO
SCL_PIN = 19          # Si4703 SCLK
RST_PIN = 6           # Si4703 RST
I2C_ID = 1            # GP18/GP19 belong to I2C1
I2C_FREQ = 100_000
REGION = "EU"         # "US", "EU" or "JP" (see _REGIONS)
INITIAL_VOLUME = 8    # 0..15
SEEK_RSSI_THRESHOLD = 0x19   # reg 0x05 SEEKTH; 0 = stops on noise
MAX_RDS_BLOCK_ERRORS = 1     # 0..3 per block; 0 = strictest, 3 = uncorrectable

# name: (BAND, SPACE, DE, lowest MHz, highest MHz, step MHz)
# DE: 0 = 75 us de-emphasis (US), 1 = 50 us (EU/JP)
_REGIONS = {
    "US": (0, 0, 0, 87.5, 108.0, 0.2),
    "EU": (0, 1, 1, 87.5, 108.0, 0.1),
    "JP": (2, 1, 1, 76.0, 90.0, 0.1),
}

# ------------------------------------------------------------- constants
_ADDR = 0x10

# reg 0x02 (POWERCFG)
_DMUTE = 0x4000
_MONO = 0x2000
_SKMODE = 0x0400      # 1 = stop at band limit, 0 = wrap around
_SEEKUP = 0x0200
_SEEK = 0x0100
_DISABLE = 0x0040
_ENABLE = 0x0001
# reg 0x03 (CHANNEL)
_TUNE = 0x8000
# reg 0x04 (SYSCONFIG1)
_RDS = 0x1000
_DE = 0x0800
# reg 0x0A (STATUSRSSI)
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


# ------------------------------------------------------- low-level access
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
    Pin(SDA_PIN, Pin.OUT, value=0)
    rst = Pin(RST_PIN, Pin.OUT, value=0)
    time.sleep_ms(10)
    rst.value(1)
    time.sleep_ms(10)
    _i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=I2C_FREQ)


# ------------------------------------------------------------- public API
def init():
    """(Re)initialise the chip. Called automatically on import."""
    global _band, _space, _de, _lo, _hi, _step
    _band, _space, _de, _lo, _hi, _step = _REGIONS[REGION]

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


def seek(up=True, wrap=True, timeout_ms=10000):
    """Seek to the next station. Returns frequency, or None if none found."""
    r = _read()
    r[0x02] |= _SEEK
    r[0x02] = (r[0x02] | _SEEKUP) if up else (r[0x02] & ~_SEEKUP)
    r[0x02] = (r[0x02] & ~_SKMODE) if wrap else (r[0x02] | _SKMODE)
    _write(r)
    s = _wait_stc(True, timeout_ms)
    failed = bool(s & _SFBL)
    r = _read()
    r[0x02] &= ~_SEEK
    _write(r)
    _wait_stc(False, timeout_ms)
    _rds.reset()
    return None if failed else get_freq()


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
        "freq": get_freq(),
        "rssi": s & 0xFF,
        "stereo": bool(s & _ST),
        "rds_sync": bool(s & _RDSS),
        "volume": r[0x05] & 0xF,
    }


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


# --------------------------------------------------------------------- RDS
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
    r = _read()
    s = r[0x0A]
    if not (s & _RDSR):
        return False
    errs = max((s >> 9) & 3,            # BLERA
               (r[0x0B] >> 14) & 3,     # BLERB
               (r[0x0B] >> 12) & 3,     # BLERC
               (r[0x0B] >> 10) & 3)     # BLERD
    if errs > MAX_RDS_BLOCK_ERRORS:
        return False
    _rds.feed(r[0x0C], r[0x0D], r[0x0E], r[0x0F])
    return True


def listen(ms=5000, interval_ms=20):
    """Blocking helper: poll RDS for ms milliseconds."""
    end = time.ticks_add(time.ticks_ms(), ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        update_rds()
        time.sleep_ms(interval_ms)


def get_rds():
    """Return what has been decoded so far.

    ps     station name (8 chars) - "" until all 4 segments were received
    rt     RadioText (up to 64 chars)
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


# ------------------------------------------------------- runs on import
init()
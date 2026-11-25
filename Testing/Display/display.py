# FM display - Nokia 5110 (PCD8544) + Raspberry Pi Pico W, MicroPython
#
# Usage from your program:
#   import display
#   display.set_freq(1001)            # 100.1 MHz (tenths of MHz)
#   display.set_station("RADIO 1")
#   display.set_song("Artist - Song")
#   display.set_volume(7)             # 0-15, bar shows for 3 s
#   display.update()                  # call often (e.g. every 20 ms) in your main loop

from machine import Pin, SPI
import framebuf
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms


# --- LCD driver ---
class LCD(framebuf.FrameBuffer):
    def __init__(self):
        self.spi = SPI(1, baudrate=4_000_000, sck=Pin(10), mosi=Pin(11))
        self.ce = Pin(13, Pin.OUT, value=1)
        self.dc = Pin(3, Pin.OUT)
        rst = Pin(4, Pin.OUT)
        self.buf = bytearray(84 * 48 // 8)
        super().__init__(self.buf, 84, 48, framebuf.MONO_VLSB)
        rst(0); sleep_ms(10); rst(1)                               # hardware reset
        self.send(0, bytes([0x21, 0xB2, 0x04, 0x14, 0x20, 0x0C]))  # init, 0xB2 = contrast

    def send(self, data_mode, data):
        self.dc(data_mode); self.ce(0)
        self.spi.write(data)
        self.ce(1)

    def show(self):
        self.send(0, bytes([0x40, 0x80]))  # go to x=0, y=0
        self.send(1, self.buf)


# --- Big 7-segment digits for the frequency ---
SEGS = {'0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F, '4': 0x66,
        '5': 0x6D, '6': 0x7D, '7': 0x07, '8': 0x7F, '9': 0x6F, '-': 0x40}

def big_text(d, s, x, y):
    for c in s:
        if c == '.':
            d.fill_rect(x, y + 14, 2, 2, 1)
            x += 4
            continue
        b = SEGS[c]
        if b & 1:  d.fill_rect(x + 2, y,      6, 2, 1)  # top
        if b & 2:  d.fill_rect(x + 8, y + 2,  2, 6, 1)  # top right
        if b & 4:  d.fill_rect(x + 8, y + 8,  2, 6, 1)  # bottom right
        if b & 8:  d.fill_rect(x + 2, y + 14, 6, 2, 1)  # bottom
        if b & 16: d.fill_rect(x,     y + 8,  2, 6, 1)  # bottom left
        if b & 32: d.fill_rect(x,     y + 2,  2, 6, 1)  # top left
        if b & 64: d.fill_rect(x + 2, y + 7,  6, 2, 1)  # middle
        x += 12
    return x


# --- State ---
lcd = LCD()
freq = None       # tenths of MHz
station = ""
song = ""
volume = 0
volume_until = 0  # time when the volume bar hides
show_song = False # which RDS text is shown now
rds_start = 0     # when the current RDS text started


# --- Setters ---
def set_freq(f):
    global freq
    freq = f

def set_station(text):
    global station
    station = text.strip()

def set_song(text):
    global song
    song = text.strip()

def set_volume(v):
    global volume, volume_until
    volume = max(0, min(v, 15))
    volume_until = ticks_add(ticks_ms(), 3000)  # show for 3 s after the last change


# --- Drawing ---
def update():
    global show_song, rds_start
    d = lcd
    now = ticks_ms()
    d.fill(0)

    # Frequency (biggest)
    f = "---.-" if freq is None else "%d.%d" % (freq // 10, freq % 10)
    width = len(f.replace('.', '')) * 12 + 4 + 25
    x = big_text(d, f, (84 - width) // 2, 0)
    d.text("MHz", x + 1, 8, 1)

    # RDS (medium): station and song take turns
    text = song if (show_song and song) or not station else station
    over = len(text) * 8 - 84                 # pixels that don't fit
    t = ticks_diff(now, rds_start)
    # short text: 5 s, long text: 1 s pause + scroll to the end + 1 s pause
    duration = 5000 if over <= 0 else 2000 + over * 40
    if t > duration:
        if station and song:
            show_song = not show_song         # swap station <-> song
        rds_start = now                       # restart (also repeats the scroll)
        t = 0
    if over <= 0:
        d.text(text, -over // 2, 22, 1)       # centered
    else:
        shift = min(max(t - 1000, 0) // 40, over)  # 1 px every 40 ms
        d.text(text, -shift, 22, 1)

    # Volume bar (smallest), only shortly after a change
    if ticks_diff(volume_until, now) > 0:
        d.rect(3, 38, 77, 10, 1)
        for i in range(15):
            if i < volume:
                d.fill_rect(5 + i * 5, 40, 3, 6, 1)      # filled tick
            else:
                d.pixel(6 + i * 5, 45, 1)                # empty tick

    d.show()
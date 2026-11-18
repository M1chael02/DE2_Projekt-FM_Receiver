from machine import Pin, I2C
import time

SDA_PIN, SCL_PIN, RST_PIN = 18, 19, 6
ADDR = 0x10

def reset_into_i2c():
    # SDIO low while RST rises -> 2-wire (I2C) mode (SEN must be high)
    Pin(SDA_PIN, Pin.OUT, value=0)
    rst = Pin(RST_PIN, Pin.OUT, value=0)
    time.sleep_ms(10)
    rst.value(1)
    time.sleep_ms(10)

reset_into_i2c()
i2c = I2C(1, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=100_000)  # takes SDA back from GPIO

print("Scan:", [hex(a) for a in i2c.scan()])   # expect ['0x10']

# --- Si4703 register access (no register address byte on the bus) ---
# Reads start at reg 0x0A and wrap around to 0x00; writes start at reg 0x02.
def read_regs():
    raw = i2c.readfrom(ADDR, 32)
    r = [(raw[i] << 8) | raw[i + 1] for i in range(0, 32, 2)]
    return r[6:] + r[:6]          # reorder to regs 0x00..0x0F

def write_regs(r):                # r = regs list; sends 0x02..0x07
    buf = bytearray()
    for v in r[2:8]:
        buf += bytes((v >> 8, v & 0xFF))
    i2c.writeto(ADDR, buf)

r = read_regs()
print("Chip ID: 0x%04X (expect 0x1242)" % r[0x00])

# Enable crystal oscillator, wait for it to settle
r[0x07] = 0x8100
write_regs(r)
time.sleep_ms(500)

# Power up, unmute
r = read_regs()
r[0x02] = 0x4001          # DMUTE | ENABLE
r[0x04] |= 0x0000
r[0x05] = 0x0000 | 0x0008 # US band/200 kHz spacing, volume 8 (0-15)
write_regs(r)
time.sleep_ms(110)

def tune(mhz):
    chan = int(round((mhz - 87.5) / 0.2))   # US/200 kHz spacing
    r = read_regs()
    r[0x03] = 0x8000 | chan                 # TUNE bit + channel
    write_regs(r)
    while not (read_regs()[0x0A] & 0x4000): # wait for STC
        time.sleep_ms(10)
    r = read_regs()
    r[0x03] &= ~0x8000                      # clear TUNE
    write_regs(r)
    while read_regs()[0x0A] & 0x4000:       # wait for STC to clear
        time.sleep_ms(10)
    s = read_regs()
    print("Tuned %.1f MHz, RSSI=%d" % (mhz, s[0x0A] & 0xFF))

tune(95.1)   # put a station you can receive here
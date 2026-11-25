# FM radio: Pico W + Si4703 (RDS) + Nokia 5110 + KY-040 encoder
# Pressing the encoder switches between volume and frequency (0.1 MHz step).

from time import ticks_ms, ticks_diff, ticks_add, sleep_ms
import fm_receiver as fm
import display
from enkoder import Encoder

PIN_CLK = 15
PIN_DT = 14
PIN_SW = 2

FREQ_MIN = 875          # tenths of MHz
FREQ_MAX = 1080
START_FREQ = 951
TUNE_DELAY_MS = 400     # tune only after the knob stops turning
LOOP_MS = 20            # RDS must be polled at least every ~40 ms

# --- Init ---
enc = Encoder(PIN_CLK, PIN_DT, PIN_SW)

volume = fm.get_volume()
freq = START_FREQ
mode = display.MODE_VOL
tune_at = None          # time when the selected frequency gets tuned
last_ps = ""
last_rt = ""

fm.set_freq(freq / 10)

display.set_volume(volume)
display.set_freq(freq)
display.set_mode(mode)


def tune():
    try:
        fm.set_freq(freq / 10)
    except OSError:     # chip timeout, the next knob turn tries again
        pass


# --- Main loop ---
while True:
    now = ticks_ms()

    # Button: switch mode
    if enc.pressed():
        mode = display.MODE_FREQ if mode == display.MODE_VOL else display.MODE_VOL
        display.set_mode(mode)

    # Knob
    step = enc.read()
    if step:
        if mode == display.MODE_VOL:
            volume = max(0, min(15, volume + step))
            fm.set_volume(volume)
            fm.mute(volume == 0)    # volume 0 on the chip is not silent
            display.set_volume(volume)
        else:
            freq += step
            if freq > FREQ_MAX:     # wrap around the band
                freq = FREQ_MIN
            elif freq < FREQ_MIN:
                freq = FREQ_MAX
            display.set_freq(freq)
            display.clear_rds()     # old RDS is no longer valid
            last_ps = last_rt = ""
            tune_at = ticks_add(now, TUNE_DELAY_MS)

    # Tune once the knob has stopped
    if tune_at is not None and ticks_diff(now, tune_at) >= 0:
        tune_at = None
        tune()

    # RDS (not while waiting for the tuning)
    if tune_at is None and fm.update_rds():
        rds = fm.get_rds()
        if rds["ps"] != last_ps:
            last_ps = rds["ps"]
            display.set_station(last_ps)
        if rds["rt"] != last_rt:
            last_rt = rds["rt"]
            display.set_song(last_rt)

    display.update()
    sleep_ms(LOOP_MS)

import time
import fm_receiver as fm 

FREQ_MHZ = 95.1 

VOLUME = 8 
STATUS_EVERY_MS = 5000

fm.set_volume(VOLUME)
f = fm.set_freq(FREQ_MHZ)

print("Tuned %.1f MHz" % f)

print("Waiting for RDS (station name takes a few seconds, RadioText longer)...")

last = {}
last_status = time.ticks_ms()

while True:
    fm.update_rds()           # must be called at least every ~40 ms
 
    rds = fm.get_rds()
    for key in ("pi", "ps", "rt", "artist", "title"):
        value = rds[key]
        if value and value != last.get(key):
            last[key] = value
            print("%-7s %s" % (key.upper() + ":", value))
 
    if time.ticks_diff(time.ticks_ms(), last_status) >= STATUS_EVERY_MS:
        last_status = time.ticks_ms()
        s = fm.get_status()
        print("[status] %.1f MHz  RSSI=%d  %s  RDS sync=%s" % (
            s["freq"], s["rssi"],
            "stereo" if s["stereo"] else "mono",
            "yes" if s["rds_sync"] else "no"))
 
    time.sleep_ms(20)
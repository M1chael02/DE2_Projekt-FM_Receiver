import display

display.set_freq(1001)          # 100.1 MHz
display.set_station("RADIO 1")
display.set_song("Artist - Song")
display.set_volume(7)           # 0-15, bar shows for 3 s

while True:
    # ... your radio code, call the set_* functions when values change ...
    display.update()            # redraw, call often
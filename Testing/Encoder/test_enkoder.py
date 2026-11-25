from machine import Pin
import time

# GPIO pin definitions (adjust to match your wiring)
PIN_CLK = 15
PIN_DT  = 14
PIN_SW  = 2

# Initialize inputs with internal pull-up resistors
clk = Pin(PIN_CLK, Pin.IN, Pin.PULL_UP)
dt  = Pin(PIN_DT, Pin.IN, Pin.PULL_UP)
sw  = Pin(PIN_SW, Pin.IN, Pin.PULL_UP)

counter = 0
last_clk = clk.value()
last_btn_time = 0

print("KY-040 encoder test started. Rotate the knob or press the button...")

while True:
    current_clk = clk.value()

    # React to the falling edge of CLK (corresponds to one detent/click)
    if current_clk != last_clk and current_clk == 0:
        if dt.value() != current_clk:
            counter += 1
            print(f"Direction: right  | Position: {counter}")
        else:
            counter -= 1
            print(f"Direction: left | Position: {counter}")

    last_clk = current_clk

    # Detect button press (active low) with 250ms debounce
    if sw.value() == 0:
        now = time.ticks_ms()
        if time.ticks_diff(now, last_btn_time) > 250:
            counter = 0
            print("Button PRESSED -> Position reset (0)")
            last_btn_time = now

    time.sleep_ms(1)
    
#Test enekodéru: Otáčíme-li doprava hodnota "position" roste, otáčíme-li doleva, hodnota "position" klesá (vždy s krokem 1).
#vytvořeno s pomocí google gemini
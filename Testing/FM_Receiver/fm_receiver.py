from machine import Pin, I2C
import time


# Configuration of pins
SDA = 18
CLK = 19
RST = 6
RPi_I2C_ID = 1

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
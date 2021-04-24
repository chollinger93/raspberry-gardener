from smbus2 import SMBus
import time

registers = {
    'CONFIG': 0x01,
    'TUPPER': 0x02,
    'TLOWERL': 0x03,
    'TCRIT': 0x04,
    'TA': 0x05,
    'MANUFACTURER_ID': 0x06,
    'DEVICE_ID': 0x07,
    'RESOLUTION': 0x08,
}

bus = SMBus(1)
address = 0x18

for k in registers:
    dat = bus.read_word_data(0x18, registers[k])
    print('{} -> {}'.format(k, dat))
    
# Parse temp
v = bus.read_word_data(0x18, 0x05)
print('Raw: {}'.format(v))
# Split in 2-complements
ub=v & 0xFF
lb=(v >> 8) & 0xFF
# Clear flags / take lower 13
ub = ub & 0x1F
print('1: {}, 2: {}'.format(ub, lb))
# Check for negative values
if (ub & 0x10) == 0x10:
    ub = ub & 0x0F
    t = 256 - (ub * 16 + lb/16)
else:
    t = ub * 16 + lb / 16
print('Current temp: {}C'.format(t))
    
    # 22.5625
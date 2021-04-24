import os
import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import statistics

# create the spi bus
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
 
# create the cs (chip select)
cs = digitalio.DigitalInOut(board.CE0)
 
# create the mcp object
mcp = MCP.MCP3008(spi, cs)
 
# create an analog input channel on pin 0
chan0 = AnalogIn(mcp, MCP.P0)

readings = []
i = 0
for x in range(0,60):
    i += 1
    val = chan0.value
    volt = chan0.voltage
    readings.append(volt)
    if int(val) != 0:
        print('Raw ADC Value: {}'.format(val))
        print('ADC Voltage: {} V'.format(chan0.voltage))
    time.sleep(1)

avg = statistics.mean(readings)
print('Avg voltage: {}'.format(avg))
print(readings)
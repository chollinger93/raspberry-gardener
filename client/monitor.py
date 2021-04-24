from board import *
import busio
import adafruit_mcp9808
import SI1145.SI1145 as SI1145
import os
import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

# mcp9808
def read_temp() -> int:
    with busio.I2C(SCL, SDA) as i2c:
        t = adafruit_mcp9808.MCP9808(i2c)
        return t.temperature

# SI1145
def read_uv(sensor: object) -> set:
    vis = sensor.readVisible()
    IR = sensor.readIR()
    UV = sensor.readUV() 
    uvIndex = UV / 100.0
    return (vis, IR, uvIndex)

# HD-38 (Aliexpress/Amazon)
def read_moisture(spi_chan: object) -> tuple:
    val = spi_chan.value
    volt = spi_chan.voltage
    return (val, volt)

def main():
    ## UV
    uv_sensor = SI1145.SI1145()

    ## SPI
    # create the spi bus
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    # create the cs (chip select)
    cs = digitalio.DigitalInOut(board.CE0)
    # create the mcp object
    mcp = MCP.MCP3008(spi, cs)
    # create an analog input channel on pin 0
    chan0 = AnalogIn(mcp, MCP.P0)

    # Read
    temp_c = read_temp()
    vis, ir, uv_ix = read_uv(uv_sensor)
    raw_moisture, volt_moisture = read_moisture(chan0)

    # Write
    # temp_c,vis_light,ir_light,uv_ix,raw_moisture,volt_moisture
    res = '{temp_c},{vis_light},{ir_light},{uv_ix},{raw_moisture},{volt_moisture}'.format(
         temp_c=temp_c,
         vis_light=vis,
         ir_light=ir,
         uv_ix=uv_ix,
         raw_moisture=raw_moisture,
         volt_moisture=volt_moisture
    )
    print(res)

if __name__ == '__main__':
    main()
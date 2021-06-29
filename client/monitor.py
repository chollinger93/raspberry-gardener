from board import *
import busio
import adafruit_mcp9808
import os
import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import platform
import getmac
import requests
import logging
import json
import argparse
from datetime import datetime, timezone

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

def get_machine_id():
    return '{}-{}'.format(platform.uname().node, getmac.get_mac_address())

def main(rest_endpoint: str, frequency_s=1, buffer_max=10, spi_in=0x0, disable_rest=False):
    if disable_rest:
        logger.warning('Rest endpoint disabled')
    buffer=[]
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
    chan0 = AnalogIn(mcp, spi_in)

    while True:
        try:
            # Read
            temp_c = read_temp()
            vis, ir, uv_ix = read_uv(uv_sensor)
            raw_moisture, volt_moisture = read_moisture(chan0)

            # Write
            # temp_c,vis_light,ir_light,uv_ix,raw_moisture,volt_moisture
            reading = {
                'sensorId': get_machine_id(),
                'tempC': temp_c,
                'visLight': vis,
                'irLight': ir,
                'uvIx': uv_ix,
                'rawMoisture': raw_moisture,
                'voltMoisture': volt_moisture,
                'measurementTs': datetime.now(timezone.utc).isoformat() # RFC 3339
            }

            # Only send if we have all 
            # UV sensor sometimes doesn't play along
            if int(vis) == 0 or int(ir) == 0 or int(volt_moisture) == 0:
                logger.warning('No measurements: {}'.format(reading))
                continue

            if not disable_rest:
                buffer.append(reading)
                logger.debug(reading)
                if len(buffer) >= buffer_max:
                    logger.debug('Flushing buffer')
                    # Send
                    logger.debug('Sending: {}'.format(json.dumps(buffer)))
                    response = requests.post(rest_endpoint, json=buffer)
                    logger.debug(response)
                    # Reset
                    buffer = []
            else:
                logger.info(reading)
        except Exception as e:
            logger.exception(e)
        finally:
            time.sleep(frequency_s)



if __name__ == '__main__':
    # Args
    parser = argparse.ArgumentParser(description='Collect sensor data')
    parser.add_argument('--rest_endpoint', dest='rest_endpoint', required=True, type=str)
    parser.add_argument('--frequency', dest='frequency_s', required=False, default=1, type=int)
    parser.add_argument('--buffer_max', dest='buffer_max', required=False, default=10, type=int)
    parser.add_argument('--spi_in', dest='spi_in', required=False, default=0, type=int)
    parser.add_argument('--disable_rest', dest='disable_rest', required=False, default=False, action='store_true')
    args = parser.parse_args()
    # Logging
    logging.basicConfig()
    formatter = logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s %(filename)s:%(funcName)s():%(lineno)d - %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if (logger.hasHandlers()):
        logger.handlers.clear()
    logger.addHandler(handler)

    # Start
    logger.warning('Starting')
    main(**vars(args))
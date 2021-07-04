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
import max44009.max44009 as m4
from smbus2 import SMBus

class Sensor():
    def __init__(self, sensor: object) -> None:
        self.sensor = sensor

    def read_metric(self) -> dict:
        """Implemented in each sensor

        Returns a `dict` of readings, mapping to the SQL schema.

        Return None if no reading. Equals NULL in DB.

        Returns:
            dict: Column -> Reading
        """
        pass

# Temp
class MCP9808_S(Sensor):
    def read_metric(self):
        with busio.I2C(SCL, SDA) as i2c:
            t = adafruit_mcp9808.MCP9808(i2c)
            return {
                'tempC': t.temperature
            }

# UV
class SI1145_S(Sensor):
    def read_metric(self):
        vis = self.sensor.readVisible()
        IR = self.sensor.readIR()
        UV = self.sensor.readUV() 
        uvIndex = UV / 100.0
        # UV sensor sometimes doesn't play along
        if int(vis) == 0 or int(IR) == 0:
            return None

        return {
            'visLight': vis,
            'irLight': IR,
            'uvIx': uvIndex
        }

# Moisture: HD-38 (Aliexpress/Amazon)
# pass spi_chan
class HD38_S(Sensor):
    def read_metric(self):
        raw_moisture = self.sensor.value
        volt_moisture = self.sensor.voltage
        if int(raw_moisture) == 0:
            return None
        return {
            'rawMoisture': raw_moisture, 
            'voltMoisture': volt_moisture
        }

# Lumen: pass MAX44009
class MAX44009_S(Sensor):
    def read_metric(self):
        return {
            'lumen': self.sensor.read_lumen_with_retry()
            }

__sensor_map__ = {
    'uv': SI1145_S,
    'temp': MCP9808_S,
    'lumen': MAX44009_S,
    'moisture': HD38_S
}

def get_machine_id():
    return '{}-{}'.format(platform.uname().node, getmac.get_mac_address())

def main(rest_endpoint: str, frequency_s=1, buffer_max=10, spi_in=0x0, disable_rest=False, *sensor_keys):
    if disable_rest:
        logger.warning('Rest endpoint disabled')
    buffer=[]

    # Create sensor objects
    sensors =  {}
    for k in sensor_keys:
        if k == 'uv':     
            # UV
            sensor = SI1145.SI1145()
        elif k == 'temp':
            # TODO: library behaves oddly
            sensor = None 
        elif k == 'lumen':
            sensor = m4.MAX44009(SMBus(1))
        elif k == 'moisture':
            ## SPI
            # create the spi bus
            spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
            # create the cs (chip select)
            cs = digitalio.DigitalInOut(board.CE0)
            # create the mcp object
            mcp = MCP.MCP3008(spi, cs)
            # create an analog input channel on pin 0
            sensor = AnalogIn(mcp, spi_in)
        else:
            logger.error(f'Unknown sensor key {k}')
            continue
        # Create
        sensors[k] = __sensor_map__[k](sensor=sensor)
    
    while True:
        try:
            # Target JSON
            reading = {
                'sensorId': get_machine_id(),
                # Metrics will come from Sensor object
                'tempC': None,
                'visLight': None,
                'irLight': None,
                'uvIx': None,
                'rawMoisture': None,
                'voltMoisture': None,
                'lumen': None,
                'measurementTs': datetime.now(timezone.utc).isoformat() # RFC 3339
            }

            # Read all
            for k in sensors:
                try:
                    sensor = sensors[k]
                    logger.debug(f'Reading {sensor}')
                    metrics = sensor.read_metric()
                    if not metrics:
                        logger.error(f'No data for sensor {k}')
                        continue
                except Exception as e:
                    logger.error(f'Error reading sensor {k}: {e}')
                    continue
                # Combine 
                reading = {**reading, **metrics}

    
            # Only send if its not disabled       
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
    parser.add_argument('--sensors', dest='sensors', required=False, default=list(__sensor_map__.keys()), type=str, nargs='+')
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
    main(args.rest_endpoint, args.frequency_s, args.buffer_max, args.spi_in, args.disable_rest, *args.sensors)
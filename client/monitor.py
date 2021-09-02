from typing import Set
import busio
import adafruit_mcp9808
import os
import time
import busio
import digitalio
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
import SI1145
import i2clcd


class Sensor():
    # We define a unique name per sensor, so we can spawn instances
    name = None

    def __init__(self, **kwargs):
        """Implemented in each sensor (constructor, duh)

        Should set `self.sensor` at least
        """
        pass

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
    name = 'temp'

    def __init__(self, **kwargs):
        # This is a weird bug in the lib - we don't set the self.sensor
        pass

    def read_metric(self):
        from board import SCL, SDA
        with busio.I2C(SCL, SDA) as i2c:
            t = adafruit_mcp9808.MCP9808(i2c)
            return {
                'tempC': t.temperature
            }

# UV
class SI1145_S(Sensor):
    name = 'uv'

    def __init__(self, **kwargs):
        self.sensor = SI1145.SI1145()

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
    name = 'moisture'

    def __init__(self, **kwargs):
        from board import SCK, MISO, MOSI, CE0
        
        # SPI
        # create the spi bus
        spi = busio.SPI(clock=SCK, MISO=MISO, MOSI=MOSI)
        # create the cs (chip select)
        cs = digitalio.DigitalInOut(CE0)
        # create the mcp object
        mcp = MCP.MCP3008(spi, cs)
        # create an analog input channel on pin 0
        self.sensor = AnalogIn(mcp, kwargs.get('spi_in', 0))

    def _translate_moisture(self, moisture):
        if moisture <= 0.77:
            return 'wet'
        elif moisture > 0.77 and moisture <= 1.5:
            return 'ok'
        else:
            return 'dry'

    def read_metric(self):
        raw_moisture = self.sensor.value
        volt_moisture = self.sensor.voltage
        rel_moisture = self._translate_moisture(volt_moisture)
        if int(raw_moisture) == 0:
            return None
        return {
            'rawMoisture': raw_moisture,
            'voltMoisture': volt_moisture,
            'relMoisture': rel_moisture,
        }

# Lumen: pass MAX44009
class MAX44009_S(Sensor):
    name = 'lumen'

    def __init__(self, **kwargs):
        self.sensor = m4.MAX44009(SMBus(1))

    def read_metric(self):
        return {
            'lumen': self.sensor.read_lumen_with_retry()
        }

class LCM106_LCD():
    """For all intents and purposes, this is a sensor.
    But it's not collecting data, just showing it"""
    name = 'lcd'

    def __init__(self):
        lcd = i2clcd.i2clcd(i2c_bus=1, i2c_addr=0x27, lcd_width=16)
        lcd.init()
        lcd.clear()
        self.sensor = lcd

    def show(self, reading):
        try:
            # Try to get the moisture
            relMoisture = reading.get('relMoisture', None)
            voltMoisture = reading.get('voltMoisture', None)
            if relMoisture and voltMoisture:
                ln1 = 'Soil: {} [{:.2f}]'.format(
                    relMoisture, voltMoisture)
            else:
                ln1 = 'Soil: N/A'
            # Try to read temp
            tempC = reading.get('tempC', None)
            if tempC:
                ln2 = 'Temp: {:.2f}C'.format(tempC)
            else:
                ln2 = 'Temp: N/A'
            # Display
            self.sensor.print_line(ln1, line=0)
            self.sensor.print_line(ln2, line=1)
        except Exception as e:
            logger.error(f'LCD failed showing data {reading}: {e}')


def get_all_subclasses(cls) -> Set[object]:
    """Gets all subclasses of a given class; Sensor in this cae 

    See: https://github.com/chollinger93/scarecrow/blob/master/scarecrow_core/plugin_base/interceptor.py

    Args:
        names: All sensor names

    Returns:
        set: All classes
    """
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in get_all_subclasses(c)])


def gen_sensors_by_name(*names):
    """Get all sensors (classes) if they match the name

    Yields:
        [type]: [description]
    """
    for cls in get_all_subclasses(Sensor):
        if cls.name in names:
            yield cls

def create_sensors(*names, spi_in=0) -> dict:
    """Actually create the sensor instances

    Args:
        spi_in (int, optional): [description]. Defaults to 0.

    Returns:
        dict: Dict of sensor objects/instances
    """
    sensors = {}
    for s in gen_sensors_by_name(*names):
        # Within here, it'll create the underlying library objects
        try:
            sensors[s.name] = s(spi_in=spi_in)
        except Exception as e:
            logger.error(f'Error creating sensor: {s.name}: {e}')
            continue
    return sensors

def get_machine_id() -> str:
    """Get a unique ID for this machine

    Returns:
        str: The ID
    """
    return '{}-{}'.format(platform.uname().node, getmac.get_mac_address())


def read_sensors(sensors: dict, lcd=None) -> dict:
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
        # RFC 3339
        'measurementTs': datetime.now(timezone.utc).isoformat()
    }

    # Read all
    for k in sensors:
        try:
            sensor = sensors[k]
            logger.debug(f'Reading {sensor.name}')
            metrics = sensor.read_metric()
            if not metrics:
                logger.error(f'No data for sensor {k}')
                continue
        except Exception as e:
            logger.error(f'Error reading sensor {k}: {e}')
            continue
        # Combine
        reading = {**reading, **metrics}

    # Power the LCD, if it's enabled
    if lcd:
        lcd.show(reading)

    return reading

def main(rest_endpoint: str, frequency_s=1, buffer_max=10, spi_in=0x0, disable_rest=False, enable_lcd=True, *sensor_keys):
    if disable_rest:
        logger.warning('Rest endpoint disabled')
    buffer = []

    # Create sensor objects
    sensors = create_sensors(*sensor_keys, spi_in=spi_in)
    
    if len(sensors) == 0:
        logger.error('No sensors specified')
        return

    # Create an LCD if we need it
    lcd = None
    if enable_lcd:
        lcd = LCM106_LCD()

    while True:
        try:
            # Read 
            reading = read_sensors(sensors, lcd)

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


# Logging
fmt = '%(asctime)s - %(name)s - %(levelname)s %(filename)s:%(funcName)s():%(lineno)d - %(message)s'
logging.basicConfig(
    format=fmt,
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
formatter = logging.Formatter(fmt=fmt)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if (logger.hasHandlers()):
    logger.handlers.clear()
logger.addHandler(handler)

if __name__ == '__main__':
    # Args
    parser = argparse.ArgumentParser(description='Collect sensor data')
    parser.add_argument('--rest_endpoint',
                        dest='rest_endpoint', required=True, type=str)
    parser.add_argument('--sensors', dest='sensors', required=False,
                        default=list(['uv', 'temp', 'lumen', 'moisture']), type=str, nargs='+', help='Sensors to use. Need to be connected')
    parser.add_argument('--frequency', dest='frequency_s',
                        required=False, default=1, type=int, help='Frequency in seconds in which to collect data')
    parser.add_argument('--buffer_max', dest='buffer_max',
                        required=False, default=10, type=int, help='Max buffer before sending data to REST endpoint')
    parser.add_argument('--spi_in', dest='spi_in',
                        required=False, default=0, type=int, help='Input SPI address. Default is 0x0.')
    parser.add_argument('--enable_lcd', dest='enable_lcd',
                        required=False, default=True, action='store_true', help='Enable the LCD?')
    parser.add_argument('--disable_rest', dest='disable_rest',
                        required=False, default=False, action='store_true', help='Whether to disable the REST sender')
    parser.add_argument('--verbose', dest='verbose',
                        required=False, default=False, action='store_true', help='Verbose mode')
    args = parser.parse_args()

    # Logger
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Start
    logger.warning('Starting')
    
    main(args.rest_endpoint, args.frequency_s, args.buffer_max,
         args.spi_in, args.disable_rest, args.enable_lcd, *args.sensors)

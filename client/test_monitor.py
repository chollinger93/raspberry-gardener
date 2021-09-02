import pytest 
from monitor import gen_sensors_by_name, create_sensors, read_sensors, SI1145_S, MCP9808_S

def test_gen_sensors_by_name():
    # Positive
    s = list(gen_sensors_by_name('uv', 'temp'))
    assert len(s) == 2
    for c in s:
        assert c in [SI1145_S, MCP9808_S]
    # Invalid
    s = list(gen_sensors_by_name('uv', None))
    assert len(s) == 1
    for c in s:
        assert c in [SI1145_S]

def test_create_sensors():
    s = create_sensors('temp', spi_in=0)
    assert len(s) == 1

def test_read_sensors():
    s = create_sensors('temp', spi_in=0)
    reading = read_sensors(s)
    # We don't have sensors for unit tests, but at least should get some values
    assert reading['sensorId'] != None 
    assert reading['measurementTs'] != None 
    assert reading['tempC'] == None
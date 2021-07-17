# Monitor

To be run on the Raspberry to collect data and send it to the REST endpoint (under `/server` of this repo).

## Usage
```
usage: monitor.py [-h] --rest_endpoint REST_ENDPOINT
                  [--sensors SENSORS [SENSORS ...]] [--frequency FREQUENCY_S]
                  [--buffer_max BUFFER_MAX] [--spi_in SPI_IN] [--disable_rest]

Collect sensor data

optional arguments:
  -h, --help            show this help message and exit
  --rest_endpoint REST_ENDPOINT
  --sensors SENSORS [SENSORS ...]
  --frequency FREQUENCY_S
  --buffer_max BUFFER_MAX
  --spi_in SPI_IN
  --disable_rest
```

e.g.

```
python3 monitor.py --rest_endpoint "http://server.local:7777"
```

## Install

### Automatic
```
Usage: ./install_client.sh --endpoint http://server.local:777 --sensors 'temp lumen moisture'
```

Please check `sbin/install_client.sh` for details.

### Manual
```
export REST_ENDPOINT="http://server.local:7777" # Customize
export SENSORS="temp lumen moisture" # Customize

mkdir -p /opt/raspberry-gardener
touch /opt/raspberry-gardener/.env.sensor.sh
echo "REST_ENDPOINT=$REST_ENDPOINT" > /opt/raspberry-gardener/.env.sensor.sh
echo "SENSORS=$SENSORS" >> /opt/raspberry-gardener/.env.sensor.sh
cp monitor.py /opt/raspberry-gardener/
cp -r max44009/ /opt/raspberry-gardener/

# Install packages as sudo if the sensor runs as sudo
sudo pip3 install -r requirements.txt
```

### Systemd
```
sudo mkdir -p /var/log/raspberry-gardener/
sudo cp garden-sensor.service /etc/systemd/system/
sudo systemctl start garden-sensor
sudo systemctl enable garden-sensor # Autostart
```

## Enable `I2C` and `SPI`
```
sudo raspi-config
# 3 -> Interface
# P4 -> SPI -> Enable
# P5 -> I2C -> Enable
```
# Monitor

To be run on the Raspberry to collect data and send it to the REST endpoint (under `/server` of this repo).

## Usage
```
usage: monitor.py [-h] --rest_endpoint REST_ENDPOINT [--frequency FREQUENCY_S]
                  [--buffer_max BUFFER_MAX] [--spi_in SPI_IN]

Collect sensor data

optional arguments:
  -h, --help            show this help message and exit
  --rest_endpoint REST_ENDPOINT
  --frequency FREQUENCY_S
  --buffer_max BUFFER_MAX
  --spi_in SPI_IN
```

e.g.

```
python3 monitor.py --rest_endpoint "http://server.local:7777"
```

## Install
```
export REST_ENDPOINT="http://server.local:7777" # Customize

sudo mkdir -p /opt/raspberry-gardener
sudo touch /opt/raspberry-gardener/.env.sensor.sh
echo "REST_ENDPOINT=$REST_ENDPOINT" | sudo tee /opt/raspberry-gardener/.env.sensor.sh
sudo cp monitor.py /opt/raspberry-gardener/

# Install packages as sudo if the sensor runs as sudo
sudo pip3 install -r requirements.txt
```

## Systemd
```
sudo mkdir -p /var/log/raspberry-gardener/
sudo cp garden-sensor.service /etc/systemd/system/
sudo systemctl start garden-sensor
sudo systemctl enable garden-sensor # Autostart
```
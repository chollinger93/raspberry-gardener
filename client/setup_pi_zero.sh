#!/bin/bash

if [[ $EUID -ne 0 ]]; then 
    echo "This script must be run as root"
    exit 1
fi

if [[ -z "${PI_IP}" || -z ${PI_DNS} || -z ${REST_ENDPOINT} || -z ${PI_ROUTER} ]]; then 
    echo "Usage: PI_IP=192.168.1.2 PI_ROUTER=192.168.1.1 PI_DNS=8.8.8.8 REST_ENDPOINT=http://server.local:7777 ./setup_pi_zero.sh"
fi 

# Install dependencies
apt-get update
apt-get install git python3 python3-pip python3-venv i2c-tools vim ntpdate

# Enable I2C, SPI
echo "Enable I2C and SPI manually by running raspi-config over ssh."
#raspi-config 

# Static IP
echo "interface wlan0" >> /etc/dhcpcd.conf
echo "static ip_address=${PI_IP}/24" >> /etc/dhcpcd.conf
echo "static routers=${PI_ROUTER}" >> /etc/dhcpcd.conf
echo "static domain_name_servers=${PI_DNS} 1.1.1.1 fd51:42f8:caae:d92e::1" >> /etc/dhcpcd.conf
echo "nameserver ${PI_DNS}" >> /etc/resolv.conf 

# Time
timedatectl set-timezone America/New_York
timedatectl set-ntp True

# Clone code 
cd /home/pi
mkdir -p /home/pi/workspace
cd /home/pi/workspace
git clone https://github.com/chollinger93/raspberry-gardener
cd raspberry-gardener/client
SENSORS="temp lumen moisture" # Customize

# Install 
mkdir -p /opt/raspberry-gardener
touch /opt/raspberry-gardener/.env.sensor.sh
echo "REST_ENDPOINT=$REST_ENDPOINT" > /opt/raspberry-gardener/.env.sensor.sh
echo "SENSORS=$SENSORS" >> /opt/raspberry-gardener/.env.sensor.sh
cp monitor.py /opt/raspberry-gardener/
cp -r max44009/ /opt/raspberry-gardener/

# Install packages as sudo if the sensor runs as sudo
pip3 install -r requirements.txt

# Systemd
mkdir -p /var/log/raspberry-gardener/
cp garden-sensor.service /etc/systemd/system/
systemctl start garden-sensor
systemctl enable garden-sensor # Autostart

# logrotate.d
cat > /etc/logrotate.d/raspberry-gardener.conf << EOF
/var/log/raspberry-gardener/* {
    daily
    rotate 1
    size 10M
    compress
    delaycompress
}
EOF
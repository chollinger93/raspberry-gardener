#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be run as root${NC}"
    exit 1
fi

if [[ -z "${PI_IP}" || -z ${PI_DNS} || -z ${PI_ROUTER} ]]; then
    echo -e "${RED}Usage: PI_IP=192.168.1.2 PI_ROUTER=192.168.1.1 PI_DNS=8.8.8.8 PI_USER=pi ./setup_pi_zero.sh${NC}"
    exit 1
fi

if [[ -z "${PI_USER}" ]]; then
    echo "Defaulting PI_USER to pi"
    PI_USER=pi
fi

# Install dependencies
apt-get update
apt-get install git python3 python3-pip python3-venv i2c-tools vim ntpdate python3-smbus zsh

# Enable I2C, SPI
echo -e "${GREEN}Enable I2C and SPI manually by running raspi-config${NC}"
raspi-config

# Static IP
echo "interface wlan0" >>/etc/dhcpcd.conf
echo "static ip_address=${PI_IP}/24" >>/etc/dhcpcd.conf
echo "static routers=${PI_ROUTER}" >>/etc/dhcpcd.conf
echo "static domain_name_servers=${PI_DNS} 1.1.1.1 fd51:42f8:caae:d92e::1" >>/etc/dhcpcd.conf
echo "nameserver ${PI_DNS}" >>/etc/resolv.conf

# Time
timedatectl set-timezone America/New_York
timedatectl set-ntp True

# Clone code
cd "/home/${PI_USER}"
mkdir -p "/home/${PI_USER}/workspace"
cd "/home/${PI_USER}/workspace"
git clone https://github.com/chollinger93/raspberry-gardener
chown -R "${PI_USER}" "/home/${PI_USER}"

# Install
echo -e "${GREEN}Run sbin/install_client.sh to finish setup${NC}"

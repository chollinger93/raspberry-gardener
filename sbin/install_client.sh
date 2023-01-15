#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

printUsage() {
    echo -e "${RED}Usage: ./install_client.sh --endpoint http://server.local:777 --sensors 'temp lumen moisture'${NC}" 1>&2
    exit 1
}

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be run as root${NC}" 1>&2
    exit 1
fi

POSITIONAL=()
while (($# > 0)); do
    case "${1}" in
    -e | --endpoint)
        REST_ENDPOINT=$2
        shift 2
        ;;
    -s | --sensors)
        SENSORS=$2
        shift 2
        ;;
    esac
done

set -- "${POSITIONAL[@]}" # restore positional params

OPTS=""

if [[ -z "${REST_ENDPOINT}" ]]; then
    echo -e "${GREEN}Defaulting to --disable_rest${NC}"
    REST_ENDPOINT=http://127.0.0.1:7777
    OPTS="--disable_rest"
fi

if [[ -z "${SENSORS}" ]]; then
    SENSORS="temp lumen moisture" # Customize
    echo -e "${GREEN}Defaulting sensors to '${SENSORS}'${NC}"
fi
export REST_ENDPOINT="${REST_ENDPOINT}"
export SENSORS="${SENSORS}"

cd "${DIR}/../client/"

mkdir -p /opt/raspberry-gardener
touch /opt/raspberry-gardener/.env.sensor.sh
echo "REST_ENDPOINT=$REST_ENDPOINT" >/opt/raspberry-gardener/.env.sensor.sh
echo "SENSORS=$SENSORS" >>/opt/raspberry-gardener/.env.sensor.sh
echo "OPTS=$OPTS" >>/opt/raspberry-gardener/.env.sensor.sh
cp monitor.py /opt/raspberry-gardener/
cp -r max44009/ /opt/raspberry-gardener/

# Install packages as sudo if the sensor runs as sudo
pip3 install -r requirements.txt

# Install apt dependencies
apt install python3-smbus

# Systemd service file
mkdir -p /var/log/raspberry-gardener/
systemctl daemon-reload
cp raspberry-gardener.service /etc/systemd/system/
systemctl start raspberry-gardener
systemctl enable raspberry-gardener # Autostart

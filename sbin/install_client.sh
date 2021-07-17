#!/bin/bash

printUsage(){
    echo "Usage: ./install_client.sh --endpoint http://server.local:777 --sensors 'temp lumen moisture'" 1>&2
    exit 1
}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi  

POSITIONAL=()
while (( $# > 0 )); do
    case "${1}" in
        -e|--endpoint)
            REST_ENDPOINT=$2
            shift 2
        ;;
        -s|--sensors)
            SENSORS=$2
            shift 2
        ;;
    esac
done

set -- "${POSITIONAL[@]}" # restore positional params

if [[ -z "${REST_ENDPOINT}" ]]; then 
    printUsage
fi  

if [[ -z "${SENSORS}" ]]; then
    SENSORS="temp lumen moisture" # Customize
    echo "Defaulting sensors to '${SENSORS}'"
fi
export REST_ENDPOINT="${REST_ENDPOINT}"
export SENSORS="${SENSORS}"

cd "${DIR}/../client/"

mkdir -p /opt/raspberry-gardener
touch /opt/raspberry-gardener/.env.sensor.sh
echo "REST_ENDPOINT=$REST_ENDPOINT" > /opt/raspberry-gardener/.env.sensor.sh
echo "SENSORS=$SENSORS" >> /opt/raspberry-gardener/.env.sensor.sh
cp monitor.py /opt/raspberry-gardener/
cp -r max44009/ /opt/raspberry-gardener/

# Install packages as sudo if the sensor runs as sudo
pip3 install -r requirements.txt

# Install apt dependencies
apt install python3-smbus

# Systemd service file
mkdir -p /var/log/raspberry-gardener/
systemctl daemon-reload
cp garden-sensor.service /etc/systemd/system/
systemctl start garden-sensor
systemctl enable garden-sensor # Autostart
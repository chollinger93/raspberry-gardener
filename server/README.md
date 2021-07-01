# Server
Collection point for multiple sensors using REST. No TSL.

## Configure

1. Create a mySQL database "sensors" 
2. Run `data.sql` (DDL)
3. `cp .env.sample.sh .env.sh`
4. Fill in mySQL connection details

## Compile & Install
```
# For x86
GOARCH=amd64 GOOS=linux go build -o /tmp/sensor-server *.go 
sudo mkdir -p /opt/raspberry-gardener
sudo cp /tmp/sensor-server /opt/raspberry-gardener
sudo cp ./.env.sh /opt/raspberry-gardener/
sudo sed -i 's/export //g' /opt/raspberry-gardener/.env.sh
```

Install `systemd` service:
```
sudo mkdir -p /var/log/raspberry-gardener/
sudo cp raspberry-gardener.service /etc/systemd/system/
sudo systemctl start raspberry-gardener
sudo systemctl enable raspberry-gardener # Autostart
```

## Unit Tests
Export all variables from your `.env.sh`.

```
go test ./*.go
```
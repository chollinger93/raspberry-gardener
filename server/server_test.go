package main

import (
	"testing"

	_ "github.com/go-sql-driver/mysql"
)

// Run all unit test with the environment file EXPORTED
func TestApp_validateSensor(t *testing.T) {
	tests := []struct {
		name    string
		SmtpCfg *SmtpConfig
		sensor  *Sensor
		wantErr bool
	}{
		{
			name:    "Valid email sent",
			SmtpCfg: NewSmtpConfig(),
			sensor: &Sensor{
				SensorId:      "unit_test",
				TempC:         4,
				VoltMoisture:  1.5, // 2.6 dry, 1.5 moist, 0.77 water
				MeasurementTs: "2021-07-01T10:00:00",
			},
			wantErr: false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			a := &App{
				SmtpCfg: tt.SmtpCfg,
			}
			if err := a.validateSensor(tt.sensor); (err != nil) != tt.wantErr {
				t.Errorf("App.validateSensor() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

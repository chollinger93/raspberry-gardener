/*CREATE DATABASE IF NOT EXISTS `sensors`;*/

CREATE OR REPLACE TABLE `sensors`.`data` (
    `sensorId`	            TEXT,
    `TempC`	                FLOAT,
    `VisLight`	            FLOAT,
    `IrLight`               FLOAT,
    `UvIx`                  FLOAT,
    `RawMoisture`           FLOAT,
    `VoltMoisture`          FLOAT,
    `MeasurementTs`         TIMESTAMP,
    `lastUpdateTimestamp`   TIMESTAMP
);

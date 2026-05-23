// sensors.h

#pragma once

struct SensorData {
    float soilMoisture;
    float temperature;
    float humidity;
    float lightLevel;
    float waterLevel;
    int rssi;
};

void initSensors();
SensorData readSensors();
#include "sensors.h"
#include "../include/config.h"
#include "../include/types.h"
#include <WiFi.h>
#include <Arduino.h>
#include <cmath>

/**
 * 📊 Sensor Module Implementation - 5 Sensors
 * Reads 5 ADC inputs, generates fake data in simulation mode
 */

// =========================================================
// SENSOR PIN ARRAY
// =========================================================
static const uint8_t sensor_pins[NUM_SENSORS] = SOIL_SENSOR_PINS;

// =========================================================
// INITIALIZATION
// =========================================================
void sensors_init() {
    DEBUG_PRINTLN("[SENSORS] Initializing 5-sensor subsystem");
    
    // Configure all 5 soil moisture pins as input
    for (int i = 0; i < NUM_SENSORS; i++) {
        pinMode(sensor_pins[i], INPUT);
        DEBUG_PRINTF("[SENSORS] Configured sensor %d on pin %d\n", i + 1, sensor_pins[i]);
    }
    
    // ADC configuration (ESP32 specific)
    // Set 12-bit resolution (0-4095)
    analogReadResolution(12);
    
    DEBUG_PRINTLN("[SENSORS] All 5 sensors initialized, ADC resolution set to 12-bit");
}

// =========================================================
// SENSOR READING (5 Sensors)
// =========================================================
SensorData sensors_read() {
    SensorData data;
    data.timestamp_ms = millis();
    
    // Read all 5 soil moisture sensors
    uint32_t sum = 0;
    for (int i = 0; i < NUM_SENSORS; i++) {
        data.soil_raw[i] = analogRead(sensor_pins[i]);
        data.soil_moisture[i] = adc_to_moisture(data.soil_raw[i]);
        sum += data.soil_moisture[i];
    }
    
    // Compute average
    data.soil_average = (uint16_t)(sum / NUM_SENSORS);
    
    // Placeholder for DHT/BME later
    data.temperature = 22.0f;
    data.humidity = 50.0f;
    
    // Get WiFi signal strength
    data.rssi = sensors_get_rssi();
    
    return data;
}

// =========================================================
// SINGLE SENSOR READ (for diagnostics)
// =========================================================
uint16_t sensors_read_single(uint8_t sensor_index) {
    if (sensor_index >= NUM_SENSORS) return 0;
    return analogRead(sensor_pins[sensor_index]);
}

// =========================================================
// SIMULATION MODE
// =========================================================

// Simulation state (persists across calls)
static SoilState sim_soil;
static bool sim_initialized = false;

void sensors_simulate_tick(SoilState *soil_sim, bool valve_is_on, float weather_factor) {
    if (!soil_sim) return;
    
    // ===== EVAPORATION =====
    float evap = (0.6f - 0.5f / 100.0f) * 0.8f * 0.20f;
    evap *= weather_factor;
    soil_sim->surface -= fmax(0.02f, evap);
    
    // ===== FLOW BETWEEN LAYERS =====
    float sr = (soil_sim->surface - soil_sim->root) * 0.08f;
    soil_sim->surface -= sr;
    soil_sim->root += sr;
    
    float rd = (soil_sim->root - soil_sim->deep) * 0.02f;
    soil_sim->root -= rd;
    soil_sim->deep += rd;
    
    // ===== VALVE EFFECT =====
    if (valve_is_on) {
        soil_sim->surface -= 8.0f;
        soil_sim->root -= 3.0f;
    }
    
    // ===== EQUILIBRIUM PULL =====
    float base = 460.0f;
    soil_sim->disturbance *= 0.96f;
    
    soil_sim->surface += (base - soil_sim->surface) * 0.015f + soil_sim->disturbance * 0.02f;
    soil_sim->root += (base - soil_sim->root) * 0.010f + soil_sim->disturbance * 0.01f;
    soil_sim->deep += (base - soil_sim->deep) * 0.006f + soil_sim->disturbance * 0.005f;
    
    // ===== CLAMP VALUES =====
    soil_sim->surface = fmax(0.0f, fmin(soil_sim->surface, 900.0f));
    soil_sim->root = fmax(0.0f, fmin(soil_sim->root, 850.0f));
    soil_sim->deep = fmax(0.0f, fmin(soil_sim->deep, 800.0f));
}

/**
 * In SIMULATION_MODE: Generate fake readings from all 5 sensors
 * Each sensor reads the same simulated soil with independent noise
 */
SensorData sensors_read_simulated() {
    SensorData data;
    
    // Initialize simulation state on first call
    if (!sim_initialized) {
        sim_soil.surface = SIM_INITIAL_SURFACE;
        sim_soil.root = SIM_INITIAL_ROOT;
        sim_soil.deep = SIM_INITIAL_DEEP;
        sim_initialized = true;
        DEBUG_PRINTLN("[SENSORS] Simulation mode initialized");
    }
    
    data.timestamp_ms = millis();
    
    // Get soil average and add per-sensor noise
    float avg = sim_soil.avg();
    uint32_t sum = 0;
    
    for (int i = 0; i < NUM_SENSORS; i++) {
        // Each sensor has independent ±2.5 noise (like Python)
        float noise = (random(-50, 51) / 100.0f) * 2.5f;
        data.soil_moisture[i] = (uint16_t)(avg + noise);
        
        // Clamp to valid range
        data.soil_moisture[i] = fmax(300, fmin(data.soil_moisture[i], 700));
        data.soil_raw[i] = data.soil_moisture[i];
        
        sum += data.soil_moisture[i];
    }
    
    // Compute average
    data.soil_average = (uint16_t)(sum / NUM_SENSORS);
    
    // Fake temperature/humidity
    data.temperature = 22.0f + (random(-10, 11) / 100.0f);
    data.humidity = 50.0f + (random(-30, 31) / 100.0f);
    
    // Fake RSSI drift
    data.rssi = -50 + random(-40, 41);
    
    return data;
}

// =========================================================
// WIFI SIGNAL
// =========================================================
int sensors_get_rssi() {
    if (WiFi.status() == WL_CONNECTED) {
        return WiFi.RSSI();
    }
    return -100;  // No signal if not connected
}

// =========================================================
// DEBUG OUTPUT
// =========================================================
void sensors_debug_print() {
    DEBUG_PRINT("[SENSORS] ");
    for (int i = 0; i < NUM_SENSORS; i++) {
        DEBUG_PRINTF("S%d:%d ", i + 1, g_control.sensors.soil_moisture[i]);
    }
    DEBUG_PRINTF("| AVG:%d | RSSI:%d\n", g_control.sensors.soil_average, g_control.sensors.rssi);
    
    #if SIMULATION_MODE
    DEBUG_PRINTF("[SIM] Surface:%.1f | Root:%.1f | Deep:%.1f | Avg:%.1f\n",
                 g_control.soil_sim.surface, g_control.soil_sim.root,
                 g_control.soil_sim.deep, g_control.soil_sim.avg());
    #endif
}

void sensors_debug_print_single(uint8_t sensor_index) {
    if (sensor_index >= NUM_SENSORS) {
        DEBUG_PRINTLN("[SENSORS] Invalid sensor index");
        return;
    }
    
    DEBUG_PRINTF("[SENSOR %d] Moisture: %d | Raw ADC: %d\n",
                 sensor_index + 1,
                 g_control.sensors.soil_moisture[sensor_index],
                 g_control.sensors.soil_raw[sensor_index]);
}
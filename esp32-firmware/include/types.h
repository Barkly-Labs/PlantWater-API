#pragma once

#include <cstdint>
#include <cstring>

/**
 * 🌱 Smart Garden Firmware - Type Definitions
 * Shared data structures for sensors, control, and networking
 */

// =========================================================
// 📊 SENSOR DATA
// =========================================================
/**
 * SensorData - Aggregated sensor readings from 5 moisture sensors
 * Contains all input data for control logic
 */
struct SensorData {
    // 5 soil moisture sensor readings (0-1000 scale)
    uint16_t soil_moisture[5];     // Array of 5 sensor readings
    uint16_t soil_raw[5];          // Raw ADC readings for debugging
    uint16_t soil_average;         // Average of all 5 sensors
    
    // Environmental sensors
    float temperature;             // Degrees C (future DHT)
    float humidity;                // Relative humidity % (future)
    
    // Network quality
    int rssi;                      // WiFi signal strength (dBm)
    
    // Timing
    uint32_t timestamp_ms;         // When reading was taken
    
    // Constructor with defaults
    SensorData() : temperature(22.0f), humidity(50.0f), 
                   rssi(-50), timestamp_ms(0) {
        for (int i = 0; i < 5; i++) {
            soil_moisture[i] = 500;
            soil_raw[i] = 0;
        }
        soil_average = 500;
    }
;

// =========================================================
// 💧 VALVE STATE
// =========================================================
/**
 * ValveState - Complete valve control state
 * Preserves the pressure-based valve model from Python
 */
struct ValveState {
    bool is_on;                 // Current valve state
    float pressure;             // Pressure accumulator (units matching Python model)
    uint8_t cooldown_ticks;    // Cooldown counter (prevents rapid switching)
    uint32_t last_switch_ms;    // Timestamp of last state change
    
    // Diagnostics
    uint32_t total_activations; // Count of times valve was turned on
    
    // Constructor
    ValveState() : is_on(false), pressure(0.0f), cooldown_ticks(0), 
                   last_switch_ms(0), total_activations(0) {}
};

// =========================================================
// 🌿 PLANT STATE
// =========================================================
/**
 * PlantState - Health and stress tracking
 * Matches Python Plant class behavior
 */
struct PlantState {
    float health;              // 0-100 (starts at 70)
    float stress;              // 0-10 (accumulates when conditions bad)
    
    // Diagnostics
    float min_health;          // Lowest health recorded
    float max_stress;          // Highest stress recorded
    
    // Constructor
    PlantState() : health(70.0f), stress(0.0f), min_health(70.0f), max_stress(0.0f) {}
};

// =========================================================
// 🌱 SOIL STATE (SIMULATION MODE)
// =========================================================
/**
 * SoilState - Simulation model for soil moisture evolution
 * Only used in SIMULATION_MODE. In hardware mode, uses real ADC readings.
 * Preserves Python Soil class behavior.
 */
struct SoilState {
    float surface;             // Surface moisture level
    float root;                // Root zone moisture level
    float deep;                // Deep soil moisture level
    
    // System disturbance (from events like rain)
    float disturbance;         // Decays slowly, prevents instant resets
    
    // Constructor
    SoilState() : surface(460.0f), root(480.0f), deep(510.0f), disturbance(0.0f) {}
    
    // Compute average (used for control decisions)
    float avg() const {
        return (surface + root) / 2.0f;
    }
};

// =========================================================
// 🔄 CONTROL STATE
// =========================================================
/**
 * ControlState - Main control loop state
 * Contains all data needed for a single update cycle
 */
struct ControlState {
    // Current inputs
    SensorData sensors;        // Latest sensor readings
    
    // System state
    ValveState valve;          // Valve control state
    PlantState plant;          // Plant health/stress
    
    // Simulation state (only if SIMULATION_MODE)
    SoilState soil_sim;        // Fake soil for testing
    
    // Timing
    uint32_t tick_count;       // Number of ticks since boot
    uint32_t last_tick_ms;     // When last tick occurred
    
    // Constructor
    ControlState() : tick_count(0), last_tick_ms(0) {}
};

// =========================================================
// 🌐 TELEMETRY DATA (FOR API)
// =========================================================
/**
 * TelemetryData - Payload sent to backend (matches Python API)
 * Maps to /api/bed-data endpoint from device.py send()
 */
struct TelemetryData {
    // Device identification
    char bed_id[32];           // "bed_1"
    
    // Sensor array (5 readings with noise)
    uint16_t sensors[5];       // 5 sensor readings with ±2.5 noise
    uint16_t average;          // Average of all sensors
    
    // State
    char valve_state[8];       // "ON" or "OFF"
    float plant_health;        // Current plant health (0-100)
    
    // Environment (from backend weather API)
    struct {
        float temp;            // Temperature
        float humidity;        // Humidity
        float sun;             // Sun intensity
    } weather;
    
    // Network
    int rssi;                  // WiFi signal strength
    
    // Timing
    uint32_t timestamp_unix;   // Seconds since epoch
    uint32_t uptime_ms;        // Device uptime
    
    // Constructor
    TelemetryData() : plant_health(70.0f), rssi(-50), 
                      timestamp_unix(0), uptime_ms(0) {
        strncpy(bed_id, "bed_1", sizeof(bed_id) - 1);
        bed_id[sizeof(bed_id) - 1] = '\0';
        
        strcpy(valve_state, "OFF");
        
        for (int i = 0; i < 5; i++) {
            sensors[i] = 500;
        }
        average = 500;
        
        weather.temp = 22.0f;
        weather.humidity = 50.0f;
        weather.sun = 0.5f;
    }
};

// =========================================================
// 📡 NETWORK STATE
// =========================================================
/**
 * NetworkState - WiFi and API connectivity
 */
struct NetworkState {
    bool wifi_connected;       // WiFi status
    bool api_reachable;        // Backend API responding
    uint32_t last_telemetry_ms;    // When last telemetry was sent
    uint32_t last_heartbeat_ms;    // When last heartbeat was sent
    uint32_t wifi_reconnect_attempts; // Retry counter
    
    // Constructor
    NetworkState() : wifi_connected(false), api_reachable(false),
                     last_telemetry_ms(0), last_heartbeat_ms(0),
                     wifi_reconnect_attempts(0) {}
};

// =========================================================
// 🎛️ GLOBAL STATE (minimized, used cautiously)
// =========================================================
/**
 * These would be instantiated in main.cpp
 * Grouped to make dependencies explicit
 */
extern ControlState g_control;      // Main control state
extern NetworkState g_network;      // Network status
extern uint32_t g_boot_time_ms;     // When device started

#endif // TYPES_H

#pragma once

/**
 * 🌱 Smart Garden Firmware - Configuration
 * ESP32-based autonomous watering system
 */

// =========================================================
// 🔧 COMPILE-TIME MODE SELECTION
// =========================================================
#define SIMULATION_MODE false   // Set to true for testing without hardware

// =========================================================
// 🔌 GPIO PIN DEFINITIONS (5 Soil Sensors)
// =========================================================
// Analog ADC inputs for 5 soil moisture sensors
#define SOIL_SENSOR_1_PIN 34    // ADC0 - Bed 1 soil moisture
#define SOIL_SENSOR_2_PIN 35    // ADC1 - Bed 2 soil moisture
#define SOIL_SENSOR_3_PIN 32    // ADC2 - Bed 3 soil moisture
#define SOIL_SENSOR_4_PIN 33    // ADC3 - Bed 4 soil moisture
#define SOIL_SENSOR_5_PIN 36    // ADC4 - Bed 5 soil moisture

// Control outputs
#define VALVE_RELAY_PIN 5       // Digital output for solenoid valve
#define HEARTBEAT_LED_PIN 2     // Optional indicator LED

// Convenience macro
#define NUM_SENSORS 5
#define SOIL_SENSOR_PINS {SOIL_SENSOR_1_PIN, SOIL_SENSOR_2_PIN, SOIL_SENSOR_3_PIN, SOIL_SENSOR_4_PIN, SOIL_SENSOR_5_PIN}

// =========================================================
// 📊 SENSOR CALIBRATION
// =========================================================
// ADC value mapping (0-4095 on ESP32)
#define SOIL_ADC_DRY 2500       // ADC value when completely dry
#define SOIL_ADC_WET 1000       // ADC value when completely wet
#define SOIL_ADC_MAX 4095       // Maximum ADC value

// Convert ADC to moisture (0-1000 scale matching Python simulator)
// This maps ADC to the "pressure units" the Python model uses
inline uint16_t adc_to_moisture(uint16_t adc_value) {
    // Clamp and invert (dry = high number, wet = low number in simulator)
    if (adc_value > SOIL_ADC_DRY) return 300;      // Very dry
    if (adc_value < SOIL_ADC_WET) return 700;      // Very wet
    // Linear interpolation between wet/dry
    return 700 - ((adc_value - SOIL_ADC_WET) * 400 / (SOIL_ADC_DRY - SOIL_ADC_WET));
}

// =========================================================
// 💧 VALVE CONTROL THRESHOLDS (from Python simulator)
// =========================================================
#define SOIL_WILTING 300        // Below this = plant under stress
#define SOIL_FIELD_CAPACITY 650 // Above this = plant under stress (too wet)
#define VALVE_ON_THRESHOLD 710  // Turn valve ON if avg > this
#define VALVE_OFF_THRESHOLD 520 // Turn valve OFF if avg < this (with cooldown)
#define VALVE_COOLDOWN_TICKS 8  // Prevent rapid on/off cycling

// =========================================================
// 🌿 PLANT HEALTH THRESHOLDS (from Python simulator)
// =========================================================
#define PLANT_IDEAL_LOW 420     // Health increases in this range
#define PLANT_IDEAL_HIGH 560    // Health increases in this range
#define PLANT_INITIAL_HEALTH 70 // Starting health value

// =========================================================
// ⏱️ TIMING CONFIGURATION
// =========================================================
#define MAIN_TICK_INTERVAL_MS 2000      // Main loop tick (2 seconds = Python TICK_RATE)
#define SENSOR_UPDATE_INTERVAL_MS 2000  // How often to read sensors
#define TELEMETRY_INTERVAL_MS 2000      // How often to send data to backend
#define HEARTBEAT_INTERVAL_MS 10000     // Heartbeat check interval (10 seconds)
#define WIFI_RECONNECT_INTERVAL_MS 5000 // Try WiFi reconnect every 5 seconds if disconnected

// =========================================================
// 🌐 NETWORK CONFIGURATION
// =========================================================
// WiFi credentials
#define WIFI_SSID "your_ssid"           // WiFi network name
#define WIFI_PASSWORD "your_password"   // WiFi password

// Backend server
#define BACKEND_HOST "192.168.1.100"    // FastAPI server address
#define BACKEND_PORT 8000               // FastAPI port
#define API_TIMEOUT_MS 2000             // HTTP request timeout
#define API_KEY "your-api-key-here"     // API authentication key

// Endpoint paths (match Python backend)
#define ENDPOINT_BED_DATA "/api/bed-data"
#define ENDPOINT_HEARTBEAT "/api/node/heartbeat"
#define ENDPOINT_WEATHER "/api/weather"

// =========================================================
// 🔐 DEVICE IDENTIFICATION
// =========================================================
#define BED_ID "bed_1"                  // Unique bed identifier
#define DEVICE_NAME "SmartGarden-ESP32" // Device model

// =========================================================
// 📝 SIMULATION PARAMETERS (used in SIMULATION_MODE)
// =========================================================
#define SIM_INITIAL_SURFACE 460.0
#define SIM_INITIAL_ROOT 480.0
#define SIM_INITIAL_DEEP 510.0
#define SIM_EVAP_BASE 0.02              // Minimum evaporation per tick
#define SIM_PRESSURE_RATE 4.0           // Pressure buildup when valve ON
#define SIM_PRESSURE_DECAY 0.97         // Pressure decay when valve OFF
#define SIM_RELEASE_RATIO 0.18          // Portion of pressure released per tick

// =========================================================
// 🐛 DEBUG & LOGGING
// =========================================================
#define DEBUG_MODE true                 // Enable serial debug output
#define DEBUG_BAUD 115200              // Serial baud rate

#if DEBUG_MODE
    #define DEBUG_PRINT(x) Serial.print(x)
    #define DEBUG_PRINTLN(x) Serial.println(x)
    #define DEBUG_PRINTF(fmt, ...) Serial.printf(fmt, ##__VA_ARGS__)
#else
    #define DEBUG_PRINT(x)
    #define DEBUG_PRINTLN(x)
    #define DEBUG_PRINTF(fmt, ...)
#endif

// =========================================================
// 📦 MEMORY CONSTRAINTS
// =========================================================
#define MAX_API_PAYLOAD_SIZE 512        // Max JSON message size
#define MAX_SENSORS_BUFFER 10           // Circular buffer for sensor readings

// =========================================================
// 🔋 POWER CONFIGURATION
// =========================================================
#define LIGHT_SLEEP_ENABLED false       // Set true for battery operation (trades latency for power)
#define LIGHT_SLEEP_MS 500              // Sleep between ticks if idle

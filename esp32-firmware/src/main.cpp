#include <Arduino.h>
#include "sensors.h"
#include "valve.h"
#include "control.h"
#include "wifi_manager.h"
#include "api.h"
#include "heartbeat.h"
#include "../include/config.h"
#include "../include/types.h"

/**
 * 🌱 Smart Garden Firmware - Main Entry Point
 * ESP32-based autonomous watering system with 5 sensors and backend integration
 * 
 * Architecture:
 *   - Local autonomy: Valve control decisions made on ESP32
 *   - 5 soil sensors: Averaged for robust readings
 *   - Networking: Telemetry to FastAPI backend
 *   - Modular: Sensors, valve, control, WiFi, API, heartbeat
 *   - Non-blocking: Uses millis() timers, no delay() in loops
 */

// =========================================================
// GLOBAL STATE
// =========================================================
ControlState g_control;         // Main control state
NetworkState g_network;         // Network status
uint32_t g_boot_time_ms;        // When device started

// Timing trackers (non-blocking)
static uint32_t last_sensor_update_ms = 0;
static uint32_t last_control_tick_ms = 0;
static uint32_t last_telemetry_ms = 0;

// =========================================================
// SETUP (runs once at boot)
// =========================================================
void setup() {
    // Initialize serial for debug output
    Serial.begin(DEBUG_BAUD);
    delay(500);  // Give serial time to stabilize
    
    DEBUG_PRINTLN("\n\n======================================");
    DEBUG_PRINTLN("🌱 SMART GARDEN FIRMWARE v2 STARTING");
    DEBUG_PRINTLN("5 Sensors + WiFi + API Backend");
    DEBUG_PRINTLN("======================================");
    
    g_boot_time_ms = millis();
    
    // Initialize all subsystems
    DEBUG_PRINTLN("\n[BOOT] Initializing subsystems...");
    
    sensors_init();        // 5 soil sensors
    valve_init();          // Solenoid valve control
    control_init();        // Automation logic
    wifi_init();           // WiFi connection
    api_init();            // Backend API
    heartbeat_init();      // Periodic checkins
    
    DEBUG_PRINTLN("[BOOT] All subsystems initialized");
    DEBUG_PRINT("[BOOT] Simulation mode: ");
    DEBUG_PRINTLN(SIMULATION_MODE ? "ENABLED" : "DISABLED");
    
    DEBUG_PRINTLN("\n[BOOT] Entering main loop");
    DEBUG_PRINTLN("======================================\n");
    
    // Set initial timing
    last_sensor_update_ms = millis();
    last_control_tick_ms = millis();
    last_telemetry_ms = millis();
}

// =========================================================
// MAIN LOOP (runs continuously, non-blocking)
// =========================================================
void loop() {
    uint32_t now_ms = millis();
    
    // ===== NON-BLOCKING WIFI MANAGEMENT =====
    wifi_tick();  // Handle reconnection logic
    
    // ===== NON-BLOCKING SENSOR UPDATE =====
    if (now_ms - last_sensor_update_ms >= SENSOR_UPDATE_INTERVAL_MS) {
        g_control.sensors = 
            #if SIMULATION_MODE
            sensors_read_simulated();
            #else
            sensors_read();  // Read all 5 sensors
            #endif
        last_sensor_update_ms = now_ms;
    }
    
    // ===== NON-BLOCKING CONTROL TICK (2 seconds) =====
    if (now_ms - last_control_tick_ms >= MAIN_TICK_INTERVAL_MS) {
        control_tick(&g_control);
        last_control_tick_ms = now_ms;
    }
    
    // ===== NON-BLOCKING TELEMETRY (2 seconds, matches Python send()) =====
    if (now_ms - last_telemetry_ms >= TELEMETRY_INTERVAL_MS) {
        if (wifi_is_connected()) {
            api_send_telemetry(&g_control);
        }
        last_telemetry_ms = now_ms;
    }
    
    // ===== NON-BLOCKING HEARTBEAT (10 seconds, matches Python heartbeat()) =====
    heartbeat_tick();
    
    // ===== OPTIONAL SLEEP FOR POWER EFFICIENCY =====
    #if LIGHT_SLEEP_ENABLED
    delay(LIGHT_SLEEP_MS);
    #else
    // Minimal CPU usage between ticks
    yield();  // Let watchdog/background tasks run
    #endif
}

// =========================================================
// DEBUG COMMAND HANDLING (via serial)
// =========================================================
void serialEvent() {
    if (!Serial.available()) return;
    
    char cmd = Serial.read();
    
    switch (cmd) {
        case 's':
            DEBUG_PRINTLN("\n--- SENSOR STATE (5 Sensors) ---");
            sensors_debug_print();
            break;
            
        case 'v':
            DEBUG_PRINTLN("\n--- VALVE STATE ---");
            valve_debug_print();
            break;
            
        case 'c':
            DEBUG_PRINTLN("\n--- CONTROL STATE ---");
            control_debug_print();
            break;
            
        case 'w':
            DEBUG_PRINTLN("\n--- WIFI STATE ---");
            wifi_debug_print();
            break;
            
        case 'n':
            DEBUG_PRINTLN("\n--- NETWORK STATE ---");
            api_debug_print();
            break;
            
        case 'b':
            DEBUG_PRINTLN("\n--- HEARTBEAT STATE ---");
            heartbeat_debug_print();
            break;
            
        case 'a':
            DEBUG_PRINTLN("\n--- ALL STATE ---");
            sensors_debug_print();
            valve_debug_print();
            control_debug_print();
            wifi_debug_print();
            api_debug_print();
            heartbeat_debug_print();
            break;
            
        case 'r':
            // Manual valve toggle for testing
            g_control.valve.is_on = !g_control.valve.is_on;
            valve_set(g_control.valve.is_on);
            DEBUG_PRINT("[MANUAL] Valve set to: ");
            DEBUG_PRINTLN(g_control.valve.is_on ? "ON" : "OFF");
            break;
            
        case 'h':
            DEBUG_PRINTLN("\n--- COMMANDS ---");
            DEBUG_PRINTLN("s - Print 5 sensor readings");
            DEBUG_PRINTLN("v - Print valve state");
            DEBUG_PRINTLN("c - Print control state");
            DEBUG_PRINTLN("w - Print WiFi state");
            DEBUG_PRINTLN("n - Print network/API state");
            DEBUG_PRINTLN("b - Print heartbeat state");
            DEBUG_PRINTLN("a - Print all state");
            DEBUG_PRINTLN("r - Toggle valve manually");
            DEBUG_PRINTLN("h - Print this help");
            DEBUG_PRINTLN("--- END COMMANDS ---\n");
            break;
    }
}


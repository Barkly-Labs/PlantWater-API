#include "heartbeat.h"
#include "api.h"
#include "wifi_manager.h"
#include "../include/config.h"
#include <Arduino.h>

/**
 * 💓 Heartbeat Module Implementation
 * Periodic health checks to backend server
 */

// =========================================================
// STATE
// =========================================================
static uint32_t last_heartbeat_ms = 0;
static uint32_t heartbeat_count = 0;

// =========================================================
// INITIALIZATION
// =========================================================
void heartbeat_init() {
    DEBUG_PRINTLN("[HEARTBEAT] Heartbeat subsystem initialized");
    DEBUG_PRINTF("[HEARTBEAT] Interval: %d ms\n", HEARTBEAT_INTERVAL_MS);
    last_heartbeat_ms = millis();
}

// =========================================================
// NON-BLOCKING HEARTBEAT TICK
// =========================================================
void heartbeat_tick() {
    uint32_t now = millis();
    
    // Only send heartbeat at configured interval
    if (now - last_heartbeat_ms < HEARTBEAT_INTERVAL_MS) {
        return;  // Not time yet
    }
    
    last_heartbeat_ms = now;
    heartbeat_count++;
    
    // Try to send heartbeat (fails silently if WiFi down)
    if (api_send_heartbeat()) {
        DEBUG_PRINTF("[HEARTBEAT] Sent (#%d)\n", heartbeat_count);
    }
}

// =========================================================
// STATE ACCESSORS
// =========================================================
uint32_t heartbeat_get_last_ms() {
    return millis() - last_heartbeat_ms;
}

// =========================================================
// DEBUG OUTPUT
// =========================================================
void heartbeat_debug_print() {
    uint32_t elapsed = heartbeat_get_last_ms();
    DEBUG_PRINTF("[HEARTBEAT] Last: %d ms ago | Count: %d\n", elapsed, heartbeat_count);
}

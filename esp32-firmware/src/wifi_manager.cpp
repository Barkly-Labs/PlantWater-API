#include "wifi_manager.h"
#include "../include/config.h"
#include "../include/types.h"
#include <WiFi.h>
#include <Arduino.h>

/**
 * 🌐 WiFi Manager Implementation
 * Non-blocking WiFi connection management
 */

// =========================================================
// CONNECTION STATE
// =========================================================
static uint32_t last_wifi_attempt_ms = 0;
static bool wifi_connecting = false;

// =========================================================
// INITIALIZATION
// =========================================================
void wifi_init() {
    DEBUG_PRINTLN("[WIFI] Initializing WiFi subsystem");
    DEBUG_PRINTF("[WIFI] SSID: %s\n", WIFI_SSID);
    
    // Start WiFi in station mode
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    wifi_connecting = true;
    last_wifi_attempt_ms = millis();
    
    DEBUG_PRINTLN("[WIFI] Connection attempt started");
}

// =========================================================
// NON-BLOCKING CONNECTION MANAGEMENT
// =========================================================
void wifi_tick() {
    // Only process reconnection attempts at intervals
    uint32_t now = millis();
    if (now - last_wifi_attempt_ms < WIFI_RECONNECT_INTERVAL_MS) {
        return;  // Wait until interval expires
    }
    
    last_wifi_attempt_ms = now;
    
    if (WiFi.status() == WL_CONNECTED) {
        if (wifi_connecting) {
            wifi_connecting = false;
            DEBUG_PRINTF("[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
            DEBUG_PRINTF("[WIFI] RSSI: %d dBm\n", WiFi.RSSI());
            g_network.wifi_connected = true;
        }
    } else {
        // Not connected, try to reconnect
        wifi_connecting = true;
        g_network.wifi_connected = false;
        g_network.wifi_reconnect_attempts++;
        
        if (g_network.wifi_reconnect_attempts % 10 == 0) {
            DEBUG_PRINTF("[WIFI] Reconnection attempt %d\n", g_network.wifi_reconnect_attempts);
        }
        
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
}

// =========================================================
// STATUS ACCESSORS
// =========================================================
bool wifi_is_connected() {
    return WiFi.status() == WL_CONNECTED;
}

int wifi_get_rssi() {
    if (wifi_is_connected()) {
        return WiFi.RSSI();
    }
    return -100;
}

uint32_t wifi_get_reconnect_attempts() {
    return g_network.wifi_reconnect_attempts;
}

// =========================================================
// DEBUG OUTPUT
// =========================================================
void wifi_debug_print() {
    DEBUG_PRINT("[WIFI] Status: ");
    if (wifi_is_connected()) {
        DEBUG_PRINTF("CONNECTED | IP: %s | RSSI: %d dBm\n",
                     WiFi.localIP().toString().c_str(), WiFi.RSSI());
    } else {
        DEBUG_PRINTF("DISCONNECTED | Attempts: %d\n", g_network.wifi_reconnect_attempts);
    }
}

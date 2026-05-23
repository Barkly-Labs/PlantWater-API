#pragma once

#include "../include/types.h"

/**
 * 🌐 WiFi Manager Module
 * Handles WiFi connection, reconnection, and status monitoring
 */

/**
 * Initialize WiFi subsystem
 * Connects to configured SSID using credentials from config.h
 */
void wifi_init();

/**
 * WiFi connection tick
 * Called from main loop to handle reconnection logic
 * Uses non-blocking connection attempts with backoff
 */
void wifi_tick();

/**
 * Check if WiFi is connected
 * Returns: true if connected, false otherwise
 */
bool wifi_is_connected();

/**
 * Get current WiFi signal strength
 * Returns: RSSI in dBm
 */
int wifi_get_rssi();

/**
 * Get connection attempt count
 * Useful for diagnostics
 */
uint32_t wifi_get_reconnect_attempts();

/**
 * Debug: Print WiFi status
 */
void wifi_debug_print();

#endif // WIFI_MANAGER_H

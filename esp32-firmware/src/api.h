#pragma once

#include "../include/types.h"

/**
 * 📡 API Module
 * Handles all communication with backend FastAPI server
 * Matches Python device.py send() and heartbeat() endpoints
 */

/**
 * Send telemetry data to backend
 * POST to /api/bed-data with sensor readings, valve state, plant health
 * Matches Python device.py send() function
 *
 * Args:
 *   - state: Current control state (sensors, valve, plant)
 * Returns: true if POST succeeded, false if failed
 */
bool api_send_telemetry(const ControlState *state);

/**
 * Send heartbeat to backend
 * POST to /api/node/heartbeat with device ID
 * Matches Python device.py heartbeat() function
 *
 * Returns: true if POST succeeded, false if failed
 */
bool api_send_heartbeat();

/**
 * Fetch weather data from backend
 * GET /api/weather
 * Returns weather struct or fails silently
 *
 * Args:
 *   - weather_out: Pointer to weather struct to fill
 * Returns: true if GET succeeded, false if failed
 */
bool api_get_weather(struct {float temp; float humidity; float sun;} *weather_out);

/**
 * Initialize API subsystem (SSL certificates, etc)
 */
void api_init();

/**
 * Debug: Print last API request status
 */
void api_debug_print();

#endif // API_H

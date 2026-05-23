#include "api.h"
#include "wifi_manager.h"
#include "../include/config.h"
#include "../include/types.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Arduino.h>
#include <cstring>
#include <time.h>

/**
 * 📡 API Module Implementation
 * Telemetry, heartbeat, and weather endpoints
 * Preserves Python device.py API behavior
 */

// =========================================================
// STATE
// =========================================================
static uint32_t last_request_time = 0;
static int last_http_code = 0;
static char last_error[64] = {0};

// =========================================================
// INITIALIZATION
// =========================================================
void api_init() {
    DEBUG_PRINTLN("[API] API subsystem initialized");
    DEBUG_PRINTF("[API] Backend: http://%s:%d\n", BACKEND_HOST, BACKEND_PORT);
}

// =========================================================
// TELEMETRY (Python send() equivalent)
// =========================================================
bool api_send_telemetry(const ControlState *state) {
    if (!state || !wifi_is_connected()) {
        return false;
    }
    
    // Create JSON payload (matches Python device.py)
    StaticJsonDocument<512> doc;
    
    doc["bed_id"] = BED_ID;
    doc["timestamp"] = millis() / 1000;  // Unix timestamp
    
    // Average soil moisture
    doc["average"] = state->sensors.soil_average;
    
    // All 5 sensor readings with noise (like Python)
    JsonArray sensors = doc.createNestedArray("sensors");
    for (int i = 0; i < 5; i++) {
        // Add per-sensor reading with ±2.5 noise
        int sensor_val = state->sensors.soil_moisture[i];
        float noise = (random(-50, 51) / 100.0f) * 2.5f;
        sensors.add((int)(sensor_val + noise));
    }
    
    // Valve state
    doc["valve_state"] = state->valve.is_on ? "ON" : "OFF";
    
    // Plant health
    doc["plant_health"] = (float)state->plant.health;
    
    // Weather
    JsonObject weather = doc.createNestedObject("weather");
    weather["temp"] = state->sensors.temperature;
    weather["humidity"] = state->sensors.humidity;
    weather["sun"] = 0.5f;  // Placeholder
    
    // Network quality
    doc["rssi"] = state->sensors.rssi;
    
    // Serialize to string
    String json_str;
    serializeJson(doc, json_str);
    
    // POST to backend
    HTTPClient http;
    String url = "http://";
    url += BACKEND_HOST;
    url += ":";
    url += BACKEND_PORT;
    url += ENDPOINT_BED_DATA;
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("x-api-key", API_KEY);
    http.setTimeout(API_TIMEOUT_MS);
    
    int httpCode = http.POST(json_str);
    bool success = (httpCode == 200);
    
    if (!success) {
        snprintf(last_error, sizeof(last_error), "HTTP %d", httpCode);
        DEBUG_PRINTF("[API] Telemetry failed: %s\n", last_error);
    } else {
        DEBUG_PRINTF("[API] Telemetry sent successfully (size: %d bytes)\n", json_str.length());
    }
    
    http.end();
    last_http_code = httpCode;
    last_request_time = millis();
    
    return success;
}

// =========================================================
// HEARTBEAT (Python heartbeat() equivalent)
// =========================================================
bool api_send_heartbeat() {
    if (!wifi_is_connected()) {
        return false;
    }
    
    HTTPClient http;
    String url = "http://";
    url += BACKEND_HOST;
    url += ":";
    url += BACKEND_PORT;
    url += ENDPOINT_HEARTBEAT;
    url += "?bed_id=";
    url += BED_ID;
    
    http.begin(url);
    http.addHeader("x-api-key", API_KEY);
    http.setTimeout(API_TIMEOUT_MS);
    
    int httpCode = http.POST("");
    bool success = (httpCode == 200);
    
    if (!success) {
        snprintf(last_error, sizeof(last_error), "HB HTTP %d", httpCode);
        DEBUG_PRINTF("[API] Heartbeat failed: %s\n", last_error);
    } else {
        DEBUG_PRINTLN("[API] Heartbeat sent");
    }
    
    http.end();
    last_http_code = httpCode;
    last_request_time = millis();
    
    return success;
}

// =========================================================
// WEATHER (Python weather update equivalent)
// =========================================================
bool api_get_weather(struct {float temp; float humidity; float sun;} *weather_out) {
    if (!weather_out || !wifi_is_connected()) {
        return false;
    }
    
    HTTPClient http;
    String url = "http://";
    url += BACKEND_HOST;
    url += ":";
    url += BACKEND_PORT;
    url += ENDPOINT_WEATHER;
    
    http.begin(url);
    http.addHeader("x-api-key", API_KEY);
    http.setTimeout(API_TIMEOUT_MS);
    
    int httpCode = http.GET();
    
    if (httpCode != 200) {
        DEBUG_PRINTF("[API] Weather fetch failed: HTTP %d\n", httpCode);
        http.end();
        return false;
    }
    
    // Parse JSON response
    String payload = http.getString();
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, payload);
    
    if (error) {
        DEBUG_PRINTF("[API] JSON parse error: %s\n", error.c_str());
        http.end();
        return false;
    }
    
    // Extract weather values
    weather_out->temp = doc["temp"] | 22.0f;
    weather_out->humidity = doc["humidity"] | 50.0f;
    weather_out->sun = doc["sun"] | 0.5f;
    
    DEBUG_PRINTF("[API] Weather: %.1f°C, %.1f%% humidity, %.2f sun\n",
                 weather_out->temp, weather_out->humidity, weather_out->sun);
    
    http.end();
    last_http_code = httpCode;
    last_request_time = millis();
    
    return true;
}

// =========================================================
// DEBUG OUTPUT
// =========================================================
void api_debug_print() {
    DEBUG_PRINT("[API] Last request: ");
    if (last_request_time == 0) {
        DEBUG_PRINTLN("None");
    } else {
        uint32_t elapsed = millis() - last_request_time;
        DEBUG_PRINTF("%d ms ago | HTTP %d\n", elapsed, last_http_code);
    }
    
    if (strlen(last_error) > 0) {
        DEBUG_PRINTF("[API] Error: %s\n", last_error);
    }
}

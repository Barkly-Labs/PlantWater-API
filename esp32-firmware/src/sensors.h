#pragma once

#include "../include/types.h"

/**
 * 📊 Sensor Module - 5 Soil Moisture Sensors
 * Handles ADC reading from 5 sensors and optional simulation
 * Abstracts hardware vs simulation mode
 */

/**
 * Initialize sensor subsystem (5 sensors)
 * Sets up ADC pins for all 5 moisture sensors
 */
void sensors_init();

/**
 * Read all 5 soil moisture sensors
 * Returns: SensorData struct with readings from all 5 sensors
 * 
 * In HARDWARE mode:
 *   - Reads real ADC values from 5 pins
 *   - Converts to moisture units
 *   - Computes average
 * 
 * In SIMULATION_MODE:
 *   - Generates fake values with state evolution
 *   - All 5 sensors track same simulated soil
 */
SensorData sensors_read();

/**
 * Read single sensor (for diagnostics)
 * Args:
 *   - sensor_index: 0-4 (which of 5 sensors)
 * Returns: Raw ADC reading from that sensor
 */
uint16_t sensors_read_single(uint8_t sensor_index);

/**
 * Update simulation state
 * Evolves soil moisture based on valve state
 * 
 * Args:
 *   - soil_sim: Pointer to SoilState to update
 *   - valve_is_on: Current valve state
 *   - weather_factor: Optional weather modifier (default 1.0)
 */
void sensors_simulate_tick(SoilState *soil_sim, bool valve_is_on, float weather_factor = 1.0f);

/**
 * Get WiFi RSSI (signal strength)
 * Returns: RSSI in dBm (-100 to -30)
 */
int sensors_get_rssi();

/**
 * Debug: Print all sensor readings
 */
void sensors_debug_print();

/**
 * Debug: Print single sensor reading
 */
void sensors_debug_print_single(uint8_t sensor_index);
#pragma once

#include "../include/types.h"

/**
 * 🎛️ Control Module
 * Core automation logic and plant health tracking
 * Preserves Python Plant class behavior exactly
 */

/**
 * Initialize control subsystem
 * Sets up initial state
 */
void control_init();

/**
 * Execute one control tick
 * This is the main update function called every MAIN_TICK_INTERVAL_MS
 * 
 * Sequence:
 *   1. Read current sensor
 *   2. Update valve based on soil moisture
 *   3. Update plant health/stress based on soil conditions
 *   4. In SIMULATION_MODE: evolve simulated soil
 *   5. Store diagnostics
 * 
 * Args:
 *   - state: Current control state (will be modified)
 */
void control_tick(ControlState *state);

/**
 * Get current plant health
 */
float control_get_plant_health();

/**
 * Get current plant stress level
 */
float control_get_plant_stress();

/**
 * Get average soil moisture (from sensors or simulation)
 */
float control_get_soil_average();

/**
 * Debug: Print current control state
 */
void control_debug_print();

#endif // CONTROL_H

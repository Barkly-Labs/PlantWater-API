#pragma once

#include "../include/types.h"

/**
 * 💧 Valve Control Module
 * Manages solenoid valve with pressure-based model
 * Preserves hysteresis behavior from Python simulator
 */

/**
 * Initialize valve subsystem
 * Sets up GPIO pins for relay control
 */
void valve_init();

/**
 * Update valve state based on soil moisture
 * Implements the core control logic from Python:
 *   - Turn ON if soil average > VALVE_ON_THRESHOLD
 *   - Turn OFF if soil average < VALVE_OFF_THRESHOLD (with cooldown protection)
 *   - Build/decay pressure based on state
 *   - Apply pressure release to soil (in sim mode)
 *
 * Args:
 *   - valve_state: Current valve state (will be modified)
 *   - soil_average: Current soil moisture average (control input)
 */
void valve_update(ValveState *valve_state, float soil_average);

/**
 * Set valve GPIO directly (ON/OFF)
 * Used internally by valve_update()
 */
void valve_set(bool on);

/**
 * Get current valve state
 * Returns: true if valve is currently ON
 */
bool valve_is_on();

/**
 * Debug: Print current valve state
 */
void valve_debug_print();

#endif // VALVE_H

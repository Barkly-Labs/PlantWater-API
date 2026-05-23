#include "valve.h"
#include "../include/config.h"
#include "../include/types.h"
#include <Arduino.h>

/**
 * 💧 Valve Control Module Implementation
 * Preserves Python Valve class behavior exactly
 */

// =========================================================
// INITIALIZATION
// =========================================================
void valve_init() {
    DEBUG_PRINTLN("[VALVE] Initializing valve subsystem");
    
    // Set relay pin as output, initially LOW (valve OFF)
    pinMode(VALVE_RELAY_PIN, OUTPUT);
    digitalWrite(VALVE_RELAY_PIN, LOW);
    
    DEBUG_PRINTLN("[VALVE] Valve relay pin set to OUTPUT, initialized OFF");
}

// =========================================================
// GPIO CONTROL
// =========================================================
void valve_set(bool on) {
    if (on) {
        digitalWrite(VALVE_RELAY_PIN, HIGH);
        DEBUG_PRINT("[VALVE] Valve turned ON at ");
        DEBUG_PRINTLN(millis());
    } else {
        digitalWrite(VALVE_RELAY_PIN, LOW);
        DEBUG_PRINT("[VALVE] Valve turned OFF at ");
        DEBUG_PRINTLN(millis());
    }
}

bool valve_is_on() {
    return digitalRead(VALVE_RELAY_PIN) == HIGH;
}

// =========================================================
// CONTROL LOGIC
// =========================================================
/**
 * Main valve update function
 * Implements the exact algorithm from Python valve.py:
 * 
 * Python pseudocode:
 *   cooldown = max(0, cooldown - 1)
 *   avg = soil.avg()
 *   
 *   if avg > 710:
 *       on = True
 *   elif avg < 520 and cooldown == 0:
 *       on = False
 *       cooldown = 8
 *   
 *   if on:
 *       pressure += 4.0
 *   else:
 *       pressure *= 0.97
 *   
 *   release = pressure * 0.18
 *   soil.surface -= release
 *   soil.root -= release * 0.4
 *   pressure -= release
 */
void valve_update(ValveState *valve_state, float soil_average) {
    if (!valve_state) return;
    
    // ===== COOLDOWN COUNTDOWN =====
    if (valve_state->cooldown_ticks > 0) {
        valve_state->cooldown_ticks--;
    }
    
    // ===== HYSTERESIS LOGIC =====
    // Turn ON: if soil too dry
    if (soil_average > VALVE_ON_THRESHOLD) {
        valve_state->is_on = true;
    }
    // Turn OFF: if soil wet enough AND cooldown expired
    else if (soil_average < VALVE_OFF_THRESHOLD && valve_state->cooldown_ticks == 0) {
        valve_state->is_on = false;
        valve_state->cooldown_ticks = VALVE_COOLDOWN_TICKS;
    }
    
    // ===== PRESSURE ACCUMULATION =====
    // Build pressure when ON, decay when OFF
    if (valve_state->is_on) {
        valve_state->pressure += SIM_PRESSURE_RATE;
    } else {
        valve_state->pressure *= SIM_PRESSURE_DECAY;
    }
    
    // ===== APPLY PRESSURE RELEASE =====
    float release = valve_state->pressure * SIM_RELEASE_RATIO;
    valve_state->pressure -= release;
    
    // In simulation mode, soil state would be updated here
    // In hardware mode, we just track the pressure for diagnostics
    
    // ===== ACTUATE GPIO =====
    valve_set(valve_state->is_on);
    
    // ===== DIAGNOSTICS =====
    if (valve_state->is_on && !digitalRead(VALVE_RELAY_PIN)) {
        valve_state->total_activations++;
    }
}

// =========================================================
// DEBUG OUTPUT
// =========================================================
void valve_debug_print() {
    DEBUG_PRINT("[VALVE] State: ");
    DEBUG_PRINT(g_control.valve.is_on ? "ON" : "OFF");
    DEBUG_PRINT(" | Pressure: ");
    DEBUG_PRINT(g_control.valve.pressure, 2);
    DEBUG_PRINT(" | Cooldown: ");
    DEBUG_PRINT(g_control.valve.cooldown_ticks);
    DEBUG_PRINT(" | Activations: ");
    DEBUG_PRINTLN(g_control.valve.total_activations);
}

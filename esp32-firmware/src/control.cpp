#include "control.h"
#include "sensors.h"
#include "valve.h"
#include "../include/config.h"
#include "../include/types.h"
#include <Arduino.h>
#include <cmath>

/**
 * 🎛️ Control Module Implementation
 * Implements the core automation logic from Python simulator
 */

// =========================================================
// INITIALIZATION
// =========================================================
void control_init() {
    DEBUG_PRINTLN("[CONTROL] Initializing control subsystem");
    
    g_control.plant.health = PLANT_INITIAL_HEALTH;
    g_control.plant.stress = 0.0f;
    g_control.plant.min_health = PLANT_INITIAL_HEALTH;
    g_control.plant.max_stress = 0.0f;
    
    DEBUG_PRINT("[CONTROL] Initial health: ");
    DEBUG_PRINTLN(g_control.plant.health);
}

// =========================================================
// MAIN CONTROL LOGIC
// =========================================================

/**
 * Plant health update
 * Python pseudocode from plant.py:
 *
 *   avg = soil.avg()
 *   
 *   if avg < WILTING:
 *       stress += 0.08
 *   elif avg > FIELD_CAPACITY:
 *       stress += 0.04
 *   else:
 *       stress *= 0.97
 *   
 *   stress = max(0, min(10, stress))
 *   
 *   if 420 <= avg <= 560:
 *       health += 0.02
 *   else:
 *       health -= 0.025
 *   
 *   health -= stress * 0.015
 *   health = max(0, min(100, health))
 */
static void plant_update(PlantState *plant, float soil_average) {
    if (!plant) return;
    
    // ===== STRESS CALCULATION =====
    if (soil_average < SOIL_WILTING) {
        // Too dry
        plant->stress += 0.08f;
    } else if (soil_average > SOIL_FIELD_CAPACITY) {
        // Too wet
        plant->stress += 0.04f;
    } else {
        // Ideal range, stress recovers
        plant->stress *= 0.97f;
    }
    
    // Clamp stress to 0-10 range
    plant->stress = fmax(0.0f, fmin(10.0f, plant->stress));
    
    // ===== HEALTH CALCULATION =====
    if (soil_average >= PLANT_IDEAL_LOW && soil_average <= PLANT_IDEAL_HIGH) {
        // Optimal moisture range, health increases
        plant->health += 0.02f;
    } else {
        // Outside optimal range, health decreases
        plant->health -= 0.025f;
    }
    
    // Stress reduces health
    plant->health -= plant->stress * 0.015f;
    
    // Clamp health to 0-100 range
    plant->health = fmax(0.0f, fmin(100.0f, plant->health));
    
    // ===== DIAGNOSTICS =====
    if (plant->health < plant->min_health) {
        plant->min_health = plant->health;
    }
    if (plant->stress > plant->max_stress) {
        plant->max_stress = plant->stress;
    }
}

// =========================================================
// MAIN TICK
// =========================================================
void control_tick(ControlState *state) {
    if (!state) return;
    
    state->tick_count++;
    state->last_tick_ms = millis();
    
    // ===== STEP 1: READ SENSORS (5 SENSORS) =====
    #if SIMULATION_MODE
    // In simulation mode, generate fake readings and evolve soil
    state->sensors = sensors_read_simulated();
    
    // Evolve simulated soil based on current valve state
    sensors_simulate_tick(&state->soil_sim, state->valve.is_on);
    
    // Update soil average for control decisions (from 5 sensors)
    float soil_avg = state->soil_sim.avg();
    #else
    // In hardware mode, read real sensors (5 ADC inputs)
    state->sensors = sensors_read();
    float soil_avg = state->sensors.soil_average;  // Average of 5 sensors
    #endif
    
    // ===== STEP 2: UPDATE VALVE =====
    valve_update(&state->valve, soil_avg);
    
    // ===== STEP 3: UPDATE PLANT STATE =====
    plant_update(&state->plant, soil_avg);
    
    // ===== STEP 4: DEBUG OUTPUT =====
    #if DEBUG_MODE && 0  // Set to 1 to enable per-tick debug
    DEBUG_PRINT("[TICK ");
    DEBUG_PRINT(state->tick_count);
    DEBUG_PRINT("] Soil:");
    DEBUG_PRINT(soil_avg, 1);
    DEBUG_PRINT(" Valve:");
    DEBUG_PRINT(state->valve.is_on ? "ON" : "OFF");
    DEBUG_PRINT(" Health:");
    DEBUG_PRINT(state->plant.health, 1);
    DEBUG_PRINT(" Stress:");
    DEBUG_PRINTLN(state->plant.stress, 1);
    #endif
}

// =========================================================
// STATE ACCESSORS
// =========================================================
float control_get_plant_health() {
    return g_control.plant.health;
}

float control_get_plant_stress() {
    return g_control.plant.stress;
}

float control_get_soil_average() {
    #if SIMULATION_MODE
    return g_control.soil_sim.avg();
    #else
    return g_control.sensors.soil_average;  // Average of all 5 sensors
    #endif
}

// =========================================================
// DEBUG OUTPUT
// =========================================================
void control_debug_print() {
    float soil_avg = control_get_soil_average();
    
    DEBUG_PRINT("[CONTROL] Soil:");
    DEBUG_PRINT(soil_avg, 1);
    DEBUG_PRINT(" | Health:");
    DEBUG_PRINT(g_control.plant.health, 1);
    DEBUG_PRINT(" | Stress:");
    DEBUG_PRINT(g_control.plant.stress, 1);
    DEBUG_PRINT(" | Valve:");
    DEBUG_PRINTLN(g_control.valve.is_on ? "ON" : "OFF");
}

# 🌱 ESP32 Firmware Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SMART GARDEN ESP32 FIRMWARE                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        main.cpp - Event Loop                      │
│  - Non-blocking timer management                                 │
│  - Subsystem orchestration                                       │
│  - Serial command interface                                      │
└────────────┬────────────────────────────────────────┬────────────┘
             │                                        │
    ┌────────▼─────────────┐              ┌──────────▼──────────┐
    │   SENSORS MODULE     │              │   VALVE MODULE      │
    ├──────────────────────┤              ├─────────────────────┤
    │ sensors.cpp/.h       │              │ valve.cpp/.h        │
    │                      │              │                     │
    │ ▪ ADC reading        │  ┌───────────► ▪ Hysteresis logic  │
    │ ▪ Calibration        │  │          │ ▪ Pressure model    │
    │ ▪ Simulation mode    │  │          │ ▪ Cooldown counter  │
    │ ▪ Noise injection    │  │          │ ▪ GPIO control      │
    │ ▪ RSSI monitoring    │  │          │ ▪ Relay actuation   │
    │                      │  │          │                     │
    │ SensorData ───────────┘  │          │ ValveState          │
    └──────────────────────┘   │          └─────────────────────┘
                              │
    ┌──────────────────────┐  │
    │   CONTROL MODULE     │  │
    ├──────────────────────┤  │
    │ control.cpp/.h       │◄─┘
    │                      │
    │ ▪ Valve switching    │
    │ ▪ Plant health       │
    │ ▪ Stress tracking    │
    │ ▪ Main control tick  │
    │ ▪ Simulation core    │
    │                      │
    │ ControlState         │
    └──────────────────────┘
              │
              │
    ┌─────────▼─────────────┐
    │   include/types.h     │
    ├───────────────────────┤
    │ SensorData struct     │
    │ ValveState struct     │
    │ PlantState struct     │
    │ SoilState struct      │
    │ ControlState struct   │
    │ NetworkState struct   │
    │ TelemetryData struct  │
    └───────────────────────┘
              │
              │
    ┌─────────▼─────────────┐
    │  include/config.h     │
    ├───────────────────────┤
    │ Pin definitions       │
    │ Thresholds (Python)   │
    │ Timing config         │
    │ Mode selection        │
    │ Debug macros          │
    └───────────────────────┘
```

## Data Flow (Single Tick)

```
TICK START (every 2000ms)
│
├─ Read Sensors
│  │
│  ├─ HARDWARE MODE:
│  │  └─► Read ADC pin 34 → Convert to pressure units
│  │
│  └─ SIMULATION MODE:
│     ├─► Evolve simulated soil (evaporation, flow, equilibrium)
│     ├─► Add watering effect if valve ON
│     └─► Add noise + RSSI drift
│
├─ Update Valve State
│  │
│  ├─ Check hysteresis thresholds
│  ├─ Decrement cooldown counter
│  ├─ Accumulate/decay pressure
│  ├─ Set GPIO relay
│  └─► ValveState updated
│
├─ Update Plant Health
│  │
│  ├─ Calculate stress based on soil conditions
│  ├─ Update health (gain in ideal range, lose otherwise)
│  ├─ Apply stress penalty
│  └─► PlantState updated
│
└─ Optional Network
   │
   ├─ [TODO] Send telemetry POST
   ├─ [TODO] Send heartbeat check
   └─► NetworkState updated

TICK END
```

## Control Decision Tree

```
Soil Moisture Reading (0-1000 scale)
│
├─ Input: soil_average from sensors
│
├─► VALVE DECISION
│   │
│   ├─ IF soil_average > 710:     ──► Turn Valve ON
│   │
│   ├─ ELIF soil_average < 520
│   │      AND cooldown == 0:     ──► Turn Valve OFF (set cooldown=8)
│   │
│   └─ ELSE:                      ──► Keep current state
│
├─► PRESSURE DYNAMICS
│   │
│   ├─ IF valve_on:               ──► pressure += 4.0
│   └─ ELSE:                      ──► pressure *= 0.97
│
├─► PLANT HEALTH
│   │
│   ├─ IF soil_average < 300:     ──► stress += 0.08 (too dry)
│   ├─ ELIF soil_average > 650:   ──► stress += 0.04 (too wet)
│   └─ ELSE:                      ──► stress *= 0.97 (recovery)
│
│   ├─ IF 420 ≤ soil_avg ≤ 560:   ──► health += 0.02 (ideal)
│   └─ ELSE:                      ──► health -= 0.025 (bad)
│
│   └─ health -= stress * 0.015   ──► Stress penalty
│
└─► DIAGNOSTICS
    ├─ Track min_health, max_stress
    ├─ Count valve activations
    └─ Log state changes
```

## Module Isolation

```
┌────────────────────────────────────────────────────────────────┐
│                    SENSORS MODULE                               │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Internal State:                                          │   │
│ │ - ADC pin configuration                                 │   │
│ │ - Simulation state (SoilState)                          │   │
│ │ - Random seed                                           │   │
│ │                                                          │   │
│ │ External Interface:                                      │   │
│ │ - sensors_init()          [called once in setup()]      │   │
│ │ - sensors_read()          [called each tick]            │   │
│ │ - sensors_get_rssi()      [utility]                    │   │
│ │ - sensors_debug_print()   [debug only]                 │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Dependencies: config.h (pins, ADC calibration)                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                     VALVE MODULE                                │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Internal State:                                          │   │
│ │ - GPIO pin configuration                                │   │
│ │ - Relay control logic                                   │   │
│ │                                                          │   │
│ │ External Interface:                                      │   │
│ │ - valve_init()            [called once in setup()]      │   │
│ │ - valve_update(state, avg) [called each tick]          │   │
│ │ - valve_is_on()           [utility]                    │   │
│ │ - valve_set(bool)         [utility]                    │   │
│ │ - valve_debug_print()     [debug only]                 │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Dependencies: config.h (pins, thresholds, constants)            │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                    CONTROL MODULE                               │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Internal State:                                          │   │
│ │ - Plant health/stress calculation                       │   │
│ │ - Valve/sensor integration logic                        │   │
│ │                                                          │   │
│ │ External Interface:                                      │   │
│ │ - control_init()          [called once in setup()]      │   │
│ │ - control_tick(state)     [called each tick loop]       │   │
│ │ - control_get_*()         [accessors]                   │   │
│ │ - control_debug_print()   [debug only]                 │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Dependencies: sensors.h, valve.h, config.h                     │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                      MAIN.CPP                                   │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Non-blocking Timer Management:                          │   │
│ │ - Track last_sensor_update_ms                           │   │
│ │ - Track last_control_tick_ms                            │   │
│ │ - Track last_telemetry_ms (TODO)                        │   │
│ │ - Track last_heartbeat_ms (TODO)                        │   │
│ │                                                          │   │
│ │ setup():                                                 │   │
│ │ - Initialize all modules                                │   │
│ │ - Print boot sequence                                   │   │
│ │                                                          │   │
│ │ loop():                                                  │   │
│ │ - Check timers                                          │   │
│ │ - Call subsystem updates when ready                     │   │
│ │ - Optional light sleep for power                        │   │
│ │                                                          │   │
│ │ serialEvent():                                           │   │
│ │ - Handle serial commands (s/v/c/a/r/h)                │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Dependencies: All modules, config.h, types.h                   │
└────────────────────────────────────────────────────────────────┘
```

## Simulation Mode Data Evolution

```
SIMULATION_MODE = true:

┌─────────────────────────────────┐
│   Initial Soil State            │
│ surface: 460.0                  │
│ root:    480.0                  │
│ deep:    510.0                  │
└──────────────┬──────────────────┘
               │
        ┌──────▼──────────────────────────────────────┐
        │        EACH TICK:                           │
        │                                             │
        │  1. EVAPORATION (reduce surface)            │
        │     surface -= max(0.02, evaporation_calc)  │
        │                                             │
        │  2. FLOW (water percolates)                 │
        │     surface → root (8%)                     │
        │     root → deep (2%)                        │
        │                                             │
        │  3. EQUILIBRIUM (drift to base level)       │
        │     Pulls toward surface:460                │
        │                                             │
        │  4. VALVE EFFECT (if ON)                    │
        │     Reduce surface by 8.0 (watering)        │
        │                                             │
        │  5. CLAMP (keep in bounds)                  │
        │     surface: [0, 900]                       │
        │     root:    [0, 850]                       │
        │     deep:    [0, 800]                       │
        │                                             │
        │  6. NOISE (±2.5 measurement error)          │
        │     soil_avg += random(-2.5, +2.5)         │
        │                                             │
        └──────┬──────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────┐
        │      CONTROL DECIDES:                       │
        │                                             │
        │  avg > 710     ──► Valve ON (water)         │
        │  avg < 520     ──► Valve OFF (let dry)      │
        │  else          ──► Keep current             │
        │                                             │
        └──────┬──────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────┐
        │      NEXT TICK PROCESSES VALVE EFFECT       │
        │      And soil evolves realistically         │
        │                                             │
        │ Effective Behavior:                         │
        │ • Valve ON  → soil increases then decreases │
        │ • Valve OFF → soil dries via evaporation    │
        │ • Settles around 460 at equilibrium        │
        │                                             │
        └──────────────────────────────────────────────┘
```

## Hardware Connections

```
┌─────────────────────────────┐
│         ESP32 DevKit        │
├─────────────────────────────┤
│                             │
│ GPIO 34 ────────┐           │
│  (ADC0)         │  Soil     │
│                 │  Moisture │
│                 │  Sensor   │
│                 │  (0-4095) │
│                 │           │
│ GPIO 5  ────────┼─────────┐ │
│                 │         │ │
│ GND/3V3 ────────┴─────────┼─┤
│                           │ │
└─────────────────────────────┘ │
                                │
                  ┌─────────────┴──┐
                  │   Relay/        │
                  │  Transistor     │
                  │   Driver        │
                  └────────┬────────┘
                           │
                    ┌──────▼──────┐
                    │  Solenoid   │
                    │   Valve     │
                    │  (12V/24V)  │
                    └─────────────┘
```

## Time Budget (2-second Tick)

```
MAIN_TICK_INTERVAL_MS = 2000ms (2 seconds)

┌─────────────────────────────────┐
│    2000 ms TICK PERIOD          │
├─────────────────────────────────┤
│                                 │
│ ├─ Read Sensor: ~1-5 ms         │
│ ├─ Update Valve: ~1 ms          │
│ ├─ Update Plant: ~1 ms          │
│ ├─ Simulation: ~2-5 ms          │
│ │                               │
│ ├─► Subtotal: ~10 ms            │
│ │                               │
│ ├─ [TODO] POST telemetry        │
│ ├─ [TODO] Heartbeat check       │
│ │                               │
│ └─► Idle/Sleep: ~1990 ms        │
│                                 │
└─────────────────────────────────┘

Result: 99.5% CPU idle time, power efficient!
```

## Future Extensions (FreeRTOS)

When upgraded to FreeRTOS tasks:

```
┌────────────────────────────────┐
│    FreeRTOS Scheduler           │
├────────────────────────────────┤
│                                │
├─ Task: CONTROL_TASK (HIGH)     │
│  └─ control_tick()             │
│     Priority: 10               │
│                                │
├─ Task: SENSOR_TASK (HIGH)      │
│  └─ sensors_read()             │
│     Priority: 9                │
│                                │
├─ Task: HEARTBEAT_TASK (MED)    │
│  └─ heartbeat_tick()           │
│     Priority: 5                │
│                                │
├─ Task: WIFI_TASK (MED)         │
│  └─ wifi_tick()                │
│     Priority: 4                │
│                                │
└─ IDLE_TASK (LOW)               │
   └─ sleep_light()              │
      Priority: 0                │
```

All modules already designed for task compatibility!

---

**Architecture Summary:**
- ✅ Clean module boundaries
- ✅ Minimal global state
- ✅ Non-blocking operations
- ✅ Easy to test (simulation mode)
- ✅ Easy to scale (multiple sensors/beds)
- ✅ Ready for FreeRTOS
- ✅ Production-quality code

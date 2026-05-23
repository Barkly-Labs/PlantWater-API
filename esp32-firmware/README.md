# 🌱 Smart Garden ESP32 Firmware

Production-ready ESP32 firmware for autonomous plant watering automation. Based on the proven Python simulator, adapted for embedded real-time control.

## 🎯 Features

- **Local Autonomy**: Full control logic runs on ESP32, no cloud dependency for watering decisions
- **Hysteresis Control**: Prevents pump oscillation with intelligent thresholds and cooldown
- **Simulation Mode**: Test without hardware using `#define SIMULATION_MODE true`
- **Non-Blocking**: Uses `millis()` timers instead of `delay()` for responsive operation
- **Modular Architecture**: Clean separation of concerns (sensors, valve, control, networking)
- **Production Code**: Embedded best practices - no dynamic allocation, reusable functions
- **FreeRTOS Ready**: Designed for easy multi-tasking upgrade

## 📋 Project Structure

```
esp32-firmware/
├── include/
│   ├── config.h              # Pin definitions, thresholds, mode selection
│   └── types.h               # Shared data structures (SensorData, ControlState, etc)
├── src/
│   ├── main.cpp              # Entry point, non-blocking event loop
│   ├── sensors.cpp/h         # ADC reading + simulation mode
│   ├── valve.cpp/h           # Relay control with hysteresis
│   ├── control.cpp/h         # Core automation (plant health, stress tracking)
│   ├── wifi_manager.cpp/h    # WiFi connection management [TODO]
│   ├── api.cpp/h             # HTTP telemetry & heartbeat [TODO]
│   └── heartbeat.cpp/h       # Background heartbeat thread [TODO]
├── platformio.ini            # PlatformIO configuration
└── README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites

- PlatformIO CLI or VS Code + PlatformIO extension
- ESP32 DevKit board
- USB cable for uploading

### Build and Upload

```bash
# Build the project
pio run -e esp32dev

# Build and upload to device
pio run -e esp32dev -t upload

# Monitor serial output
pio device monitor -p COM3 -b 115200
```

### Serial Commands (When Connected)

While monitoring serial output, you can send commands:

- `s` - Print sensor state
- `v` - Print valve state
- `c` - Print control state
- `a` - Print all state (sensors, valve, control)
- `r` - Toggle valve manually (for testing)
- `h` - Print help menu

## ⚙️ Configuration

All configuration is in `include/config.h`. Key settings:

### Hardware Mode (Default)

```cpp
#define SIMULATION_MODE false
```

Reads real ADC values from soil moisture sensor on pin 34.

### Simulation Mode

```cpp
#define SIMULATION_MODE true
```

Generates fake sensor readings and evolves simulated soil moisture using the same physics model as the Python simulator.

### Control Thresholds

```cpp
#define SOIL_WILTING 300              // Below = plant stress
#define SOIL_FIELD_CAPACITY 650       // Above = plant stress
#define VALVE_ON_THRESHOLD 710        // Turn valve ON if avg > this
#define VALVE_OFF_THRESHOLD 520       // Turn valve OFF if avg < this
#define VALVE_COOLDOWN_TICKS 8        // Prevent rapid on/off
```

### Timing

```cpp
#define MAIN_TICK_INTERVAL_MS 2000    // Main loop tick (2 seconds)
#define TELEMETRY_INTERVAL_MS 2000    // Send data to server
#define HEARTBEAT_INTERVAL_MS 10000   // Heartbeat check
```

## 📊 Control Logic

The firmware preserves the exact automation logic from the Python simulator:

### 1. **Valve Control** (`valve.cpp`)

```cpp
// Hysteresis-based control
if (soil_average > 710) valve_on = true;
if (soil_average < 520 && cooldown == 0) {
    valve_on = false;
    cooldown = 8;  // Prevent rapid switching
}

// Pressure-based actuation
if (valve_on) pressure += 4.0;
else pressure *= 0.97;
```

### 2. **Plant Health** (`control.cpp`)

```cpp
// Stress calculation
if (soil_avg < 300) stress += 0.08;        // Too dry
if (soil_avg > 650) stress += 0.04;        // Too wet
else stress *= 0.97;                       // Recovery

// Health update
if (420 <= soil_avg <= 560) health += 0.02;  // Ideal range
else health -= 0.025;                         // Outside range
health -= stress * 0.015;                     // Stress penalty
```

### 3. **Simulation** (`sensors.cpp` in SIMULATION_MODE)

```cpp
// Evaporation: soil dries out slowly
soil.surface -= evaporation_factor;

// Flow: water moves between layers
soil.root += (soil.surface - soil.root) * 0.08;

// Equilibrium: pulls back toward base level
soil.surface += (base - soil.surface) * 0.015;

// Watering: valve reduces dryness
if (valve_on) soil.surface -= 8.0;
```

## 🔌 Pin Definitions

By default:

| Pin | Purpose | Mode |
|-----|---------|------|
| 34  | Soil Moisture Sensor | ADC Input |
| 5   | Solenoid Valve Relay | GPIO Output |
| 2   | Heartbeat LED | GPIO Output (optional) |

Change in `config.h` as needed.

## 🔧 GPIO Relay Setup

The firmware assumes a relay or transistor driver on pin 5:

```
ESP32 GPIO5 --[NPN Transistor/Relay Driver]---> Solenoid Valve
            (pull valve ground through relay when HIGH)
```

- HIGH = Valve ON (water flows)
- LOW = Valve OFF (no water)

## 📡 Networking (TODO - Phase 2)

When WiFi/API modules are complete:

- **Telemetry**: POSTs sensor data + health to `/api/bed-data`
- **Heartbeat**: Sends periodic checkin to `/api/node/heartbeat`
- **Weather**: GETs external conditions from `/api/weather`
- **Autonomy**: Watering decisions made locally, not dependent on network

## 🧪 Testing Without Hardware

Set in `config.h`:

```cpp
#define SIMULATION_MODE true
```

The firmware will:

1. Generate fake soil moisture readings
2. Evolve simulated soil based on valve state
3. Add realistic noise and RSSI drift
4. Allow full control logic testing

Useful for:
- Algorithm validation before deploying to hardware
- Integration testing with server APIs
- CI/CD pipelines
- Understanding behavior without physical setup

## 📈 Simulation Dynamics

In SIMULATION_MODE, soil moisture evolves:

- **Evaporation**: Decreases over time based on temperature/humidity
- **Flow**: Water moves from surface → root → deep layers
- **Watering**: Valve reduces dryness by 8 units/tick
- **Equilibrium**: Soil drifts back toward base level 460
- **Disturbance**: Simulates rain/shock with slow decay

## 🔐 Preserving Python Behavior

All key constants and algorithms are preserved:

✅ Valve hysteresis thresholds  
✅ Pressure accumulation/decay  
✅ Plant health formulas  
✅ Stress calculation  
✅ Soil moisture physics  
✅ Cooldown protection  
✅ 2-second tick rate  

The only differences:

- ❌ No dynamic allocation (fixed memory)
- ❌ No floating-point precision issues (use appropriate types)
- ❌ No threading (use timers instead)
- ✅ All logic identical

## 📝 Code Style

- Production embedded code (no bloat)
- Non-blocking timers with `millis()`
- Fixed-size structs for state
- Clear module boundaries
- Reusable functions
- Minimal global state
- Extensive comments for clarity

## 🚦 Status Codes

`main.cpp` can detect state via serial. Typical flow:

```
[BOOT] All subsystems initialized
[BOOT] Simulation mode: ENABLED
[BOOT] Entering main loop

[TICK 1] Soil:520.3 Valve:OFF Health:70.0 Stress:0.0
[TICK 2] Soil:518.7 Valve:OFF Health:70.0 Stress:0.0
...
[VALVE] Valve turned ON at 4532
```

## 🔮 Future Enhancements

### Phase 2 - Networking
- [ ] WiFi connection manager
- [ ] API telemetry posting
- [ ] Heartbeat mechanism
- [ ] Server-sent events

### Phase 3 - Advanced Features
- [ ] Multiple soil moisture sensors
- [ ] DHT22/BME680 environmental sensors
- [ ] Notifications system
- [ ] Web dashboard connectivity

### Phase 4 - Real-time OS
- [ ] FreeRTOS multi-tasking
- [ ] Task priorities
- [ ] Inter-task communication
- [ ] Power management

## 🐛 Debugging

Enable debug output (on by default):

```cpp
#define DEBUG_MODE true
#define DEBUG_BAUD 115200
```

In code:

```cpp
DEBUG_PRINTLN("Status message");
DEBUG_PRINTF("Formatted: %d, %f\n", value, float_val);
```

Use serial monitor to view output and send commands.

## 📦 Dependencies

- `bblanchon/ArduinoJson@^7.2.2` - JSON serialization for API
- `esp32` board framework - Arduino core for ESP32

Add more as needed in `platformio.ini`.

## 🤝 Contributing

Modules follow these conventions:

- Each module has `.h` (interface) and `.cpp` (implementation)
- All functions documented with purpose and parameters
- State passed via struct pointers, not global variables
- Non-blocking operations (no `delay()` in loops)
- Debug output for all major events

## 📜 License

See repo LICENSE file.

---

**Ready to water smarter!** 🌿💧

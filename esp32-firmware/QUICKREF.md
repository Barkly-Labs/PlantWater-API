# 🌱 Quick Reference Guide

## Build & Test (30 seconds)

### Compile
```bash
cd esp32-firmware
pio run -e esp32dev
```

### Upload
```bash
pio run -e esp32dev -t upload
```

### Monitor
```bash
pio device monitor -p COM3 -b 115200
```

## Serial Commands

| Command | Function |
|---------|----------|
| `s` | Print sensor state |
| `v` | Print valve state |
| `c` | Print control state |
| `a` | Print all state |
| `r` | Toggle valve manually |
| `h` | Print help |

## Key Files

| File | Purpose |
|------|---------|
| `include/config.h` | Pin definitions, thresholds |
| `include/types.h` | Data structures |
| `src/main.cpp` | Entry point, event loop |
| `src/control.cpp` | Core automation |
| `src/valve.cpp` | Relay control |
| `src/sensors.cpp` | ADC + simulation |

## Configuration

### Toggle Simulation Mode
```cpp
// in include/config.h
#define SIMULATION_MODE true   // or false for hardware
```

### Change Watering Thresholds
```cpp
#define VALVE_ON_THRESHOLD 710      // Water when dry
#define VALVE_OFF_THRESHOLD 520     // Stop watering when wet
```

### Change Pins
```cpp
#define SOIL_MOISTURE_PIN 34   // ADC input
#define VALVE_RELAY_PIN 5      // GPIO relay
```

## Expected Behavior

### Simulation Mode
```
[BOOT] Simulation mode: ENABLED
[TICK 1] Soil:520.3 Valve:OFF Health:70.0 Stress:0.0
[TICK 2] Soil:518.7 Valve:OFF Health:70.0 Stress:0.0
...
[VALVE] Valve turned ON at 4532
[TICK 50] Soil:710.0 Valve:ON Health:70.2 Stress:0.0
```

### Hardware Mode
```
[BOOT] Simulation mode: DISABLED
[SENSORS] Sensor init complete
[VALVE] Valve relay pin set to OUTPUT
...
[TICK 1] Soil reading from ADC pin 34
```

## Control Thresholds

| Threshold | Value | Meaning |
|-----------|-------|---------|
| WILTING | 300 | Below = plant stress |
| FIELD_CAPACITY | 650 | Above = plant stress |
| IDEAL_LOW | 420 | Start of health gain |
| IDEAL_HIGH | 560 | End of health gain |
| VALVE_ON | 710 | Turn valve ON if above |
| VALVE_OFF | 520 | Turn valve OFF if below |

## Health Formula

```
if 420 ≤ soil ≤ 560: health += 0.02  (ideal)
else:                 health -= 0.025  (bad)

health -= stress × 0.015              (stress penalty)
```

## Stress Formula

```
if soil < 300:   stress += 0.08  (too dry)
if soil > 650:   stress += 0.04  (too wet)
else:            stress *= 0.97  (recovery)

stress: clamped to [0, 10]
```

## Valve Control

```
if soil > 710:              valve ON  (pressure builds)
if soil < 520 AND cooldown==0: valve OFF (cooldown=8)

pressure: if ON  → += 4.0
          if OFF → *= 0.97
```

## File Tree

```
esp32-firmware/
├── platformio.ini              (build config)
├── README.md                   (user guide)
├── ARCHITECTURE.md             (system design)
├── IMPLEMENTATION.md           (technical details)
├── PROJECT_OVERVIEW.md         (overview)
│
├── include/
│   ├── config.h               (pins, thresholds)
│   └── types.h                (structs)
│
└── src/
    ├── main.cpp               (entry point)
    ├── sensors.h/cpp          (ADC + simulation)
    ├── valve.h/cpp            (relay control)
    ├── control.h/cpp          (automation)
    ├── wifi_manager.h/cpp     [TODO]
    ├── api.h/cpp              [TODO]
    └── heartbeat.h/cpp        [TODO]
```

## Typical Debug Session

```bash
# Terminal 1: Build and upload
cd esp32-firmware
pio run -e esp32dev -t upload

# Terminal 2: Monitor
pio device monitor -p COM3 -b 115200

# Output appears...
# Type 'a' and press Enter

>>> a
[SENSORS] Soil: 520 | Raw ADC: 1234 | RSSI: -50
[VALVE] State: OFF | Pressure: 0.00 | Cooldown: 0 | Activations: 0
[CONTROL] Soil:520.0 | Health:70.0 | Stress:0.0 | Valve:OFF
```

## Hardware Wiring

```
ESP32              Sensor/Relay
────────────────────────────────
GPIO34 (ADC0) ──── Soil Moisture ADC
GPIO5  (GPIO) ──── Relay Driver (NPN transistor)
GND    ──────────── GND (common)
3V3    ──────────── VCC (sensor power)

Relay ────────────► Solenoid Valve (12/24V)
```

## Troubleshooting

### Won't compile
- Check `platformio.ini` for correct board/framework
- Verify `include/` paths in `.h` files
- Update PlatformIO: `pio pkg update -g`

### Sensor reading always 0
- Check ADC pin definition in `config.h`
- Verify hardware connection
- Try simulation mode first: `#define SIMULATION_MODE true`

### Valve won't turn on
- Check GPIO pin in `config.h`
- Verify relay/transistor wiring
- Test with manual command: press `r` in serial

### Weird health values
- Expected range: 0-100
- Should stabilize around 70
- Check soil average in serial output

## Commands Summary

```
Build:    pio run -e esp32dev
Upload:   pio run -e esp32dev -t upload
Monitor:  pio device monitor -b 115200

Simulation: #define SIMULATION_MODE true  (in config.h)
Hardware:   #define SIMULATION_MODE false (in config.h)

Serial:   s/v/c/a/r/h commands
```

## Next Steps

1. **Test Simulation Mode**: `#define SIMULATION_MODE true`
2. **Build**: `pio run`
3. **Upload**: `pio run -t upload`
4. **Monitor**: `pio device monitor`
5. **Send 'a' command**: View all state

Then proceed to Phase 2 (WiFi/API) or hardware testing.

---

For detailed info, see:
- `README.md` - Complete guide
- `ARCHITECTURE.md` - System design
- `IMPLEMENTATION.md` - Technical details

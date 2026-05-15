import requests
import random
import time
import threading
import math
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# =========================================================
# 🌐 CONFIG
# =========================================================
SERVER = "http://127.0.0.1:8000"

load_dotenv()
API_KEY = os.getenv("GARDEN_API_KEY")
HEADERS = {"x-api-key": API_KEY}

BED_ID = "bed_1"

# =========================================================
# 🌱 SOIL MODEL
# =========================================================
SOIL_DRY = 850
SOIL_WET = 250
IDEAL_SOIL = 520

SAFE_LOW = 500
SAFE_HIGH = 560
LOW_RECOVERY = 440
FIELD_CAPACITY = 600

# =========================================================
# 🌊 VALVE / HARDWARE MODEL
# =========================================================
MIN_SWITCH_TIME = 8
VALVE_LAG = 2.5
WATER_BUFFER_RATE = 6
ABSORPTION_RATE = 0.55

valve_state = False
last_switch_time = 0
valve_command_time = 0
water_buffer = 0.0

# =========================================================
# 🌿 BIOLOGICAL STATE
# =========================================================
soil_state = random.uniform(500, 650)
plant_health = 70.0
root_stress = 0.0

# =========================================================
# 📡 SENSOR DRIFT STATE
# =========================================================
sensor_bias = 0.0

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {
    "temp": 22,
    "humidity": 50,
    "sun": 0.5,
}

# =========================================================
# 💓 HEARTBEAT
# =========================================================
def heartbeat_loop():
    while True:
        try:
            requests.post(
                f"{SERVER}/api/node/heartbeat",
                params={"bed_id": BED_ID},
                headers=HEADERS,
                timeout=2
            )
        except:
            pass
        time.sleep(10)

# =========================================================
# 🌦️ WEATHER
# =========================================================
def update_weather():
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🌿 SENSOR (WITH DRIFT)
# =========================================================
def read_sensor(value):
    global sensor_bias

    sensor_bias += random.uniform(-0.02, 0.02)
    sensor_bias *= 0.995

    noise = random.uniform(-2.5, 2.5)
    return value + noise + sensor_bias

# =========================================================
# 🌿 PHYSICS ENGINE
# =========================================================
# NEW: layered water model
surface_water = 0.0  # add this globally


def simulate():
    global soil_state, plant_health, root_stress, water_buffer, surface_water

    # 🌬️ evaporation (top layer loses more)
    evap = (
        max(0, WEATHER["temp"] - 18) * 0.25 +
        WEATHER["sun"] * 0.8 +
        (100 - WEATHER["humidity"]) * 0.12
    ) * 0.2

    # 🌊 valve adds to surface (NOT directly to roots)
    if valve_state:
        surface_water += WATER_BUFFER_RATE

    # 🌊 infiltration (slow movement into soil)
    infiltration = surface_water * 0.25
    surface_water -= infiltration

    # 🌱 root absorption (what actually affects soil sensor)
    absorbed = infiltration * ABSORPTION_RATE

    # 🌿 soil update (ROOT ZONE ONLY)
    soil_state -= evap
    soil_state += absorbed

    # 🌿 equilibrium pull (prevents runaway drift)
    soil_state += 0.02 * (IDEAL_SOIL - soil_state)

    # 🌊 saturation runoff (prevents infinite water gain)
    if soil_state > FIELD_CAPACITY:
        runoff = (soil_state - FIELD_CAPACITY) * 0.4
        soil_state -= runoff
        root_stress += 0.05  # 🌿 overwatering stress

    soil_state = max(SOIL_WET, min(SOIL_DRY, soil_state))

    # =====================================================
    # 🌱 ROOT STRESS (smarter)
    # =====================================================
    if soil_state < 450:
        root_stress += 0.04  # drought
    elif soil_state > 600:
        root_stress += 0.06  # drowning
    else:
        root_stress *= 0.97  # recovery

    root_stress = max(0, min(10, root_stress))

    # =====================================================
    # 🌱 PLANT HEALTH (more realistic)
    # =====================================================
    if SAFE_LOW <= soil_state <= SAFE_HIGH:
        plant_health += 0.06
    elif 450 <= soil_state < SAFE_LOW or SAFE_HIGH < soil_state <= 600:
        plant_health -= 0.01
    else:
        plant_health -= 0.035

    # stress hurts more than watering helps
    plant_health -= root_stress * 0.025

    plant_health = max(0, min(100, plant_health))

    return soil_state
# =========================================================
# 🎛️ VALVE CONTROL (REAL HARDWARE BEHAVIOR)
# =========================================================
def apply_valve(soil):
    global valve_state, last_switch_time, valve_command_time

    now = time.time()

    # 🧊 debounce switching
    if now - last_switch_time < MIN_SWITCH_TIME:
        return

    # 💧 valve lag (hardware delay)
    if valve_state and now - valve_command_time < VALVE_LAG:
        return

    # 🌿 safe zone = OFF
    if SAFE_LOW <= soil <= SAFE_HIGH:
        valve_state = False
        last_switch_time = now
        return

    # 🌵 emergency hydration
    if soil < LOW_RECOVERY:
        valve_state = True
        valve_command_time = now
        last_switch_time = now
        return

    # 🌿 controlled irrigation
    if soil < IDEAL_SOIL - 25:
        valve_state = True
        valve_command_time = now
        last_switch_time = now
        return

    valve_state = False

# =========================================================
# 📡 TELEMETRY (WITH PACKET LOSS SIM)
# =========================================================
def send(soil):
    if random.random() < 0.03:
        return  # simulate packet loss

    sensors = [read_sensor(soil) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json={
                "bed_id": BED_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sensors": sensors,
                "average": avg,
                "valve_state": "ON" if valve_state else "OFF",
                "plant_health": plant_health,
                "rssi": random.randint(-70, -40),
            },
            headers=HEADERS,
            timeout=3
        )
    except:
        pass

    print(
        f"ADC {avg:.0f} | SOIL {soil:.1f} | "
        f"VALVE {valve_state} | HEALTH {plant_health:.1f}"
    )

# =========================================================
# 🔁 MAIN LOOP
# =========================================================
def run():
    print("🌿 FINAL REALISTIC SINGLE-BED SIM STARTED")

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    global soil_state

    while True:
        update_weather()

        soil = simulate()
        noisy = read_sensor(soil)

        apply_valve(noisy)
        send(noisy)

        time.sleep(2)

# =========================================================
# 🚀 START
# =========================================================
if __name__ == "__main__":
    run()
import requests
import random
import time
import threading
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

LOW_RECOVERY = 440
SAFE_LOW = 500
SAFE_HIGH = 560

# =========================================================
# 🌊 VALVE BEHAVIOR (HARDWARE-LIKE)
# =========================================================
MIN_SWITCH_TIME = 8
WATER_COMMIT_TIME = 6
WATER_BUFFER_RATE = 6
ABSORPTION_RATE = 0.55

valve_state = False
last_switch_time = 0
water_start_time = 0

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {
    "temp": 22,
    "humidity": 50,
    "sun": 0.5,
}

# =========================================================
# 🌱 STATE
# =========================================================
soil_state = random.uniform(500, 650)
plant_health = 70.0
water_buffer = 0.0

rssi_state = random.uniform(-65, -45)

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
# 🌦️ WEATHER DYNAMICS
# =========================================================
def update_weather():
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🌿 SOIL PHYSICS (REALISTIC BALANCE)
# =========================================================
def simulate():
    global soil_state, plant_health, water_buffer

    evap = (
        max(0, WEATHER["temp"] - 18) * 0.25 +
        WEATHER["sun"] * 0.8 +
        (100 - WEATHER["humidity"]) * 0.12
    )

    evap = max(0.2, evap) * 0.2

    # 🌊 irrigation input
    if valve_state:
        water_buffer += WATER_BUFFER_RATE

    absorbed = water_buffer * ABSORPTION_RATE
    water_buffer -= absorbed

    # 🌱 soil update
    soil_state -= evap
    soil_state += absorbed

    # natural equilibrium drift
    soil_state += 0.015 * (IDEAL_SOIL - soil_state)

    soil_state = max(SOIL_WET, min(SOIL_DRY, soil_state))

    # =====================================================
    # 🌱 PLANT HEALTH MODEL (SMOOTHED)
    # =====================================================

    if SAFE_LOW <= soil_state <= SAFE_HIGH:
        plant_health += 0.05
    elif 430 <= soil_state < SAFE_LOW or SAFE_HIGH < soil_state <= 610:
        plant_health -= 0.01
    else:
        plant_health -= 0.03

    if valve_state:
        plant_health += 0.01

    plant_health = max(0, min(100, plant_health))

    return soil_state

# =========================================================
# 📡 SENSOR NOISE
# =========================================================
def read_sensor(value):
    return value + random.uniform(-3, 3)

# =========================================================
# 🎛️ PID (soft advisory only)
# =========================================================
def compute_watering_signal(soil):
    error = soil - IDEAL_SOIL
    return error

# =========================================================
# 🌊 VALVE CONTROLLER (NO CHATTER DESIGN)
# =========================================================
def apply_valve(soil):
    global valve_state, last_switch_time, water_start_time

    now = time.time()

    # 🧊 enforce minimum switch delay
    if now - last_switch_time < MIN_SWITCH_TIME:
        return

    # 💧 commit window (prevents mid-cycle flipping)
    if valve_state:
        if now - water_start_time < WATER_COMMIT_TIME:
            return

    # 🌿 safe zone = forced OFF
    if SAFE_LOW <= soil <= SAFE_HIGH:
        valve_state = False
        last_switch_time = now
        return

    # 🌵 emergency hydration
    if soil < LOW_RECOVERY:
        valve_state = True
        water_start_time = now
        last_switch_time = now
        return

    # 🧠 controlled watering (only if clearly dry)
    signal = compute_watering_signal(soil)

    if soil < IDEAL_SOIL - 20 and signal > 0:
        valve_state = True
        water_start_time = now
        last_switch_time = now
        return

    # 🌿 default OFF
    valve_state = False

# =========================================================
# 📡 TELEMETRY
# =========================================================
def send(soil):
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
                "rssi": int(rssi_state),
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
    print("🌿 FINAL CLEAN ESP32 SIM (REALISTIC PHYSICS + NO CHATTER) STARTED")

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
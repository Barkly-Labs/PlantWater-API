import requests
import random
import time
import threading
from datetime import datetime
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

SOIL_TYPE = {"drain": 1.0, "retain": 1.0}

# =========================================================
# 🎛️ PID
# =========================================================
Kp, Ki, Kd = 0.18, 0.001, 0.04
INTEGRAL_CLAMP = 800
MAX_WATER_TIME = 6
DEADZONE = 25

# =========================================================
# 🌊 VALVE CONTROL
# =========================================================
WATER_ON_THRESHOLD = 560
WATER_OFF_THRESHOLD = 540
LOW_SOIL_RECOVERY = 440
MIN_SWITCH_TIME = 8

valve_state = False
last_switch_time = time.time()
post_water_lock = 0  # 🌿 prevents immediate re-trigger

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {
    "temp": 22,
    "humidity": 50,
    "rain": False,
    "sun": 0.5,
}

# =========================================================
# 🌱 STATE
# =========================================================
soil_state = random.uniform(500, 650)
soil_prev = soil_state
soil_velocity = 0.0

plant_health = 70.0
water_buffer = 0.0

integral = 0.0
last_error = 0.0
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
# 🌦️ WEATHER UPDATE
# =========================================================
def update_weather():
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🌿 PHYSICS ENGINE (STABLE REALISM LOOP)
# =========================================================
def simulate():
    global soil_state, soil_prev, soil_velocity
    global plant_health, water_buffer

    # 🌬️ evaporation
    evap = (
        max(0, WEATHER["temp"] - 18) * 0.3 +
        WEATHER["sun"] * 0.9 +
        (100 - WEATHER["humidity"]) * 0.1
    ) * 0.25

    evap *= SOIL_TYPE["drain"]

    # 🌱 plant uptake
    plant_effect = 0.10 * (plant_health / 100)

    # 💧 irrigation input (smoothed pump behavior)
    if valve_state:
        water_buffer += 3

    absorbed = water_buffer * 0.45
    water_buffer -= absorbed

    # 🌿 core soil dynamics
    soil_state -= evap
    soil_state += absorbed
    soil_state += plant_effect

    # 🌿 equilibrium pull (stability anchor)
    soil_state += 0.03 * (IDEAL_SOIL - soil_state)

    # 📉 clamp
    soil_state = max(SOIL_WET, min(SOIL_DRY, soil_state))

    # 📊 velocity tracking
    soil_velocity = soil_state - soil_prev
    soil_prev = soil_state

    # 🌱 plant health
    if 470 <= soil_state <= 580:
        plant_health += 0.05
    elif soil_state > 780 or soil_state < 330:
        plant_health -= 0.08
    else:
        plant_health -= 0.015

    plant_health = max(0, min(100, plant_health))

    return soil_state

# =========================================================
# 📡 SENSOR NOISE
# =========================================================
def read_sensor(value):
    return value + random.uniform(-3, 3)

# =========================================================
# 🎛️ PID CONTROLLER
# =========================================================
def compute_watering_time(soil):
    global integral, last_error

    error = soil - IDEAL_SOIL

    if abs(error) < DEADZONE:
        return 0

    if soil < IDEAL_SOIL:
        return 0

    integral += error
    integral = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, integral))

    derivative = error - last_error
    last_error = error

    control = Kp * error + Ki * integral + Kd * derivative

    return max(0, min(MAX_WATER_TIME, control))

# =========================================================
# 🌊 VALVE CONTROL (FIXED + STABLE OSCILLATION)
# =========================================================
def apply_valve(soil):
    global valve_state, last_switch_time, post_water_lock

    now = time.time()

    if now - last_switch_time < MIN_SWITCH_TIME:
        return

    # 🔒 post irrigation cooldown (CRITICAL STABILITY FIX)
    if now < post_water_lock:
        if valve_state:
            valve_state = False
            last_switch_time = now
        return

    # 🌿 strong OFF condition (prevents sticky ON)
    if valve_state and soil < WATER_OFF_THRESHOLD:
        valve_state = False
        last_switch_time = now
        post_water_lock = now + 10
        return

    # 🌿 safety overflow cutoff
    if valve_state and soil > 650:
        valve_state = False
        last_switch_time = now
        post_water_lock = now + 10
        return

    # 🌵 emergency recovery
    if soil < LOW_SOIL_RECOVERY:
        valve_state = True
        last_switch_time = now
        return

    # 🌱 normal activation
    if not valve_state and soil > WATER_ON_THRESHOLD:
        duration = compute_watering_time(soil)

        if duration > 0:
            valve_state = True
            last_switch_time = now

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
                "timestamp": datetime.utcnow().isoformat(),
                "sensors": sensors,
                "average": avg,
                "valve_state": "ON" if valve_state else "OFF",
                "plant_health": plant_health,
                "rssi": int(rssi_state)
            },
            headers=HEADERS,
            timeout=3
        )
    except:
        pass

    print(f"ADC {avg:.0f} | SOIL {soil:.1f} | VALVE {valve_state} | HEALTH {plant_health:.1f}")

# =========================================================
# 🔁 MAIN LOOP
# =========================================================
def run():
    print("🌿 FINAL STABLE ESP32 SIM STARTED")

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
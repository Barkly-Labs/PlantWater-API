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

SAFE_LOW = 400
SAFE_HIGH = 500
TARGET_SOIL = 470

# =========================================================
# 🌊 WATER SYSTEM
# =========================================================
WATER_BUFFER_RATE = 8
MIN_WATERING_TIME = 8.0
COOLDOWN_TIME = 18.0

valve_state = "OFF"
cycle_state = "IDLE"
cycle_start = 0

# =========================================================
# 🧪 SPIKE TEST MODE
# =========================================================
INJECT_SPIKE = True
INJECT_STRENGTH = 900.0
INJECT_DECAY = 0.85

# =========================================================
# 🌿 STATE
# =========================================================
soil = random.uniform(420, 520)
surface_water = 0.0
plant_health = 70.0
root_stress = 0.0

last_soil = soil

# =========================================================
# 🧠 PID
# =========================================================
Kp, Ki, Kd = 0.08, 0.010, 0.020
pid_i = 0.0

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {"temp": 22, "humidity": 50, "sun": 0.5}

def update_weather():
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 📡 SENSOR NOISE
# =========================================================
def sensor(v):
    return v + random.uniform(-1.5, 1.5)

# =========================================================
# 💓 HEARTBEAT
# =========================================================
def heartbeat():
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
# 🌿 PHYSICS ENGINE
# =========================================================
def simulate():
    global soil, surface_water, plant_health, root_stress
    global INJECT_SPIKE, INJECT_STRENGTH

    evap = (
        (WEATHER["temp"] - 20) * 0.03 +
        WEATHER["sun"] * 0.4 +
        (0.6 - WEATHER["humidity"] / 100) * 0.6
    )
    evap = max(0.1, min(1.2, evap)) * 0.2

    # 💧 irrigation input
    if valve_state == "ON":
        surface_water += WATER_BUFFER_RATE * 1.3

    infiltration = surface_water * 0.18
    surface_water -= infiltration * 0.8
    absorbed = infiltration * 0.9

    soil -= evap
    soil += absorbed

    # 🧪 spike injection
    if INJECT_SPIKE:
        soil += INJECT_STRENGTH
        INJECT_STRENGTH *= INJECT_DECAY
        if INJECT_STRENGTH < 1:
            INJECT_SPIKE = False

    # stabilization drift
    soil -= 0.001 * (soil - 480)

    soil = max(SOIL_WET, min(SOIL_DRY, soil))

    # 🌱 plant response
    if soil < SAFE_LOW:
        root_stress += 0.05
    elif soil > SAFE_HIGH:
        root_stress += 0.04
    else:
        root_stress *= 0.96

    root_stress = max(0, min(10, root_stress))

    if SAFE_LOW <= soil <= SAFE_HIGH:
        plant_health += 0.05
    else:
        plant_health -= 0.02

    plant_health -= root_stress * 0.02
    plant_health = max(0, min(100, plant_health))

    return soil

# =========================================================
# 🌊 PID CONTROLLER
# =========================================================
def controller(s):
    global valve_state, cycle_state, cycle_start
    global pid_i, last_soil

    now = time.time()

    error = TARGET_SOIL - s
    d = s - last_soil

    pid_i += error * 0.01
    pid_i = max(-50, min(50, pid_i))

    output = Kp * error + Ki * pid_i - Kd * d
    control = max(0, min(output, 1))

    # IDLE → START WATERING
    if cycle_state == "IDLE" and control > 0.25:
        valve_state = "ON"
        cycle_state = "WATERING"
        cycle_start = now

    # WATERING LOGIC
    if cycle_state == "WATERING":
        if now - cycle_start < MIN_WATERING_TIME:
            last_soil = s
            return

        if SAFE_LOW <= s <= SAFE_HIGH or control < 0.1:
            valve_state = "OFF"
            cycle_state = "COOLDOWN"
            cycle_start = now
            pid_i *= 0.5

    # COOLDOWN RESET
    if cycle_state == "COOLDOWN":
        if now - cycle_start > COOLDOWN_TIME:
            cycle_state = "IDLE"

    last_soil = s

# =========================================================
# 📡 SEND TO API (GUARANTEED VALID SCHEMA)
# =========================================================
def send(s):
    sensors = [sensor(s) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    payload = {
        "bed_id": BED_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),

        "soil": float(s),
        "average": float(avg),
        "sensors": [float(x) for x in sensors],

        # 🔥 ALWAYS STRING (FIXED)
        "valve_state": valve_state,

        "plant_health": float(plant_health),
        "rssi": random.randint(-70, -40),
    }

    try:
        r = requests.post(
            f"{SERVER}/api/bed-data",
            json=payload,
            headers=HEADERS,
            timeout=3
        )

        if r.status_code != 200:
            print("❌ SERVER:", r.status_code, r.text)

    except Exception as e:
        print("❌ SEND ERROR:", e)

    print(f"SOIL {s:.1f} | VALVE {valve_state} | AVG {avg:.1f} | HP {plant_health:.1f}")

# =========================================================
# 🔁 MAIN LOOP
# =========================================================
def run():
    print("🌿 CLEAN SMART GARDEN SIM STARTED")

    threading.Thread(target=heartbeat, daemon=True).start()

    global soil, last_soil

    while True:
        update_weather()

        soil_val = simulate()
        controller(soil_val)
        send(soil_val)

        time.sleep(2)

# =========================================================
# 🚀 START
# =========================================================
if __name__ == "__main__":
    run()
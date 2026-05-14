import requests
import random
import time
import threading
import os
from datetime import datetime
from dotenv import load_dotenv

# =========================================================
# 🌐 CONFIG
# =========================================================
SERVER = "http://127.0.0.1:8000"

load_dotenv()
API_KEY = os.getenv("GARDEN_API_KEY")
HEADERS = {"x-api-key": API_KEY} if API_KEY else {}

BED_ID = "bed_1"

# =========================================================
# 🌱 PHYSICAL SOIL STATE
# =========================================================
soil = {
    "top": random.uniform(500, 650),
    "mid": random.uniform(520, 700),
    "deep": random.uniform(550, 750),
}

plant_health = 70.0

water_buffer = 0.0

# =========================================================
# ⚙️ DEVICE STATE
# =========================================================
valve = False
last_switch = time.time()

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {
    "temp": 22.0,
    "humidity": 50.0,
    "sun": 0.5,
    "rain": False
}

# =========================================================
# 🌱 CONSTANTS (BALANCED TUNING FIX)
# =========================================================
SOIL_MIN = 200
SOIL_MAX = 900

DRY_THRESHOLD = 650
WET_THRESHOLD = 500

MIN_SWITCH_TIME = 8

EVAP_SCALE = 0.32        # 🔼 stronger drying (FIX)
DIFFUSION = 0.12
ROOT_UPTAKE = 0.08

MAX_FLOW = 8.0

# NEW: saturation drainage (FIX for "stuck wet")
DRAIN_TOP = 0.025
DRAIN_MID = 0.018
SATURATION_POINT = 680

# water retention correction (FIX)
BUFFER_LEAK = 0.10

# =========================================================
# 🌿 PHYSICS
# =========================================================
def evaporation():
    return (
        max(0, WEATHER["temp"] - 18) * 0.28 +
        WEATHER["sun"] * 0.85 +
        (100 - WEATHER["humidity"]) * 0.12
    ) * EVAP_SCALE + random.uniform(-0.4, 0.4)

def plant_uptake():
    return ROOT_UPTAKE * (plant_health / 100) + random.uniform(0.2, 0.6)

def simulate_physics():
    global plant_health, water_buffer

    evap = evaporation()
    uptake = plant_uptake()

    # 💧 irrigation input
    if valve:
        water_buffer += random.uniform(3.0, MAX_FLOW)

    # 🔧 FIX: buffer slowly leaks (prevents infinite wet lock)
    water_buffer *= (1 - BUFFER_LEAK)

    # 💧 delayed absorption
    absorbed = water_buffer * 0.30
    water_buffer -= absorbed

    # 🌿 TOP LAYER
    soil["top"] += evap + absorbed
    soil["top"] -= soil["top"] * DIFFUSION

    # 🌿 SATURATION DRAINAGE FIX
    if soil["top"] > SATURATION_POINT:
        soil["top"] -= (soil["top"] - SATURATION_POINT) * DRAIN_TOP

    # 🌿 MID LAYER
    soil["mid"] += (soil["top"] - soil["mid"]) * DIFFUSION
    soil["mid"] -= uptake

    if soil["mid"] > SATURATION_POINT:
        soil["mid"] -= (soil["mid"] - SATURATION_POINT) * DRAIN_MID

    # 🌿 DEEP LAYER
    soil["deep"] += (soil["mid"] - soil["deep"]) * DIFFUSION
    soil["deep"] -= max(0, soil["deep"] - 780) * 0.03  # 🔼 stronger gravity drain

    # clamp
    for k in soil:
        soil[k] = max(SOIL_MIN, min(SOIL_MAX, soil[k]))

    avg = (soil["top"] + soil["mid"] + soil["deep"]) / 3

    # 🌱 plant response
    if 480 <= avg <= 580:
        plant_health += 0.04
    elif avg > 750 or avg < 320:
        plant_health -= 0.10
    else:
        plant_health -= 0.02

    plant_health = max(0, min(100, plant_health))

    return avg

# =========================================================
# 📡 SENSOR LAYER
# =========================================================
def read_sensor(true_value):
    return true_value + random.uniform(-4, 4) + random.uniform(-0.01, 0.01)

# =========================================================
# 🎛️ CONTROLLER
# =========================================================
def control(avg, sensor):
    global valve, last_switch

    now = time.time()

    if now - last_switch < MIN_SWITCH_TIME:
        return

    if not valve and sensor > DRY_THRESHOLD:
        valve = True
        last_switch = now

    elif valve and sensor < WET_THRESHOLD:
        valve = False
        last_switch = now

# =========================================================
# 🌦️ WEATHER
# =========================================================
def update_weather():
    WEATHER["temp"] += random.uniform(-0.15, 0.15)
    WEATHER["humidity"] += random.uniform(-0.6, 0.6)
    WEATHER["sun"] += random.uniform(-0.03, 0.03)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 📡 TELEMETRY (API SAFE)
# =========================================================
def send(avg, sensor):
    sensors = [sensor + random.uniform(-3, 3) for _ in range(5)]
    avg_sensor = sum(sensors) / len(sensors)

    payload = {
        "bed_id": BED_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "sensors": sensors,
        "average": avg_sensor,
        "valve_state": "ON" if valve else "OFF",
        "plant_health": plant_health,
        "rssi": int(random.uniform(-65, -45))
    }

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json=payload,
            headers=HEADERS,
            timeout=2
        )
    except:
        pass

    print(f"{BED_ID} | soil:{avg:.1f} | sensor:{sensor:.1f} | valve:{valve} | health:{plant_health:.1f}")

# =========================================================
# 📡 HEARTBEAT
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
# 🔁 MAIN LOOP
# =========================================================
def loop():
    print("🌿 FIXED ESP32 DIGITAL TWIN (BALANCED HYDROLOGY) STARTED")

    while True:
        update_weather()

        avg_true = simulate_physics()
        sensor = read_sensor(avg_true)

        control(avg_true, sensor)
        send(avg_true, sensor)

        time.sleep(2)

# =========================================================
# 🚀 START
# =========================================================
if __name__ == "__main__":
    threading.Thread(target=heartbeat, daemon=True).start()
    loop()
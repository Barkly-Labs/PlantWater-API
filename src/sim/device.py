import requests
import random
import time
import threading
from datetime import datetime
import os
from dotenv import load_dotenv

# =========================
# 🌐 CONFIG
# =========================
SERVER = "http://127.0.0.1:8000"

load_dotenv()
API_KEY = os.getenv("GARDEN_API_KEY")
HEADERS = {"x-api-key": API_KEY} if os.getenv("GARDEN_API_KEY") else {}

BED_ID = "bed_1"

# =========================
# 🌱 SOIL LIMITS
# =========================
SOIL_MIN = 200
SOIL_MAX = 900
IDEAL_SOIL = 520

WATER_ON = 560
WATER_OFF = 500
MIN_SWITCH = 8

MAX_FLOW = 8.0

DIFFUSION = 0.12
ROOT_UPTAKE = 0.08
EVAP_SCALE = 0.22

# =========================
# 🌦️ WEATHER
# =========================
WEATHER = {
    "temp": 22.0,
    "humidity": 50.0,
    "sun": 0.5,
    "rain": False
}

# =========================
# 🌱 SOIL (3-LAYER PHYSICS)
# =========================
class Soil:
    def __init__(self):
        self.top = random.uniform(450, 650)
        self.mid = random.uniform(500, 700)
        self.deep = random.uniform(520, 750)

    def avg(self):
        return (self.top + self.mid + self.deep) / 3

soil = Soil()

plant_health = 70.0

# =========================
# ⚙️ DEVICE STATE
# =========================
valve = False
last_switch = time.time()

# =========================
# 🌿 SENSOR NOISE (ESP32 ADC STYLE)
# =========================
def read_sensor(value):
    return value + random.uniform(-4, 4)

# =========================
# 🌬️ EVAPORATION
# =========================
def evaporation():
    return (
        max(0, WEATHER["temp"] - 18) * 0.25 +
        WEATHER["sun"] * 0.8 +
        (100 - WEATHER["humidity"]) * 0.1
    ) * EVAP_SCALE + random.uniform(-0.3, 0.3)

# =========================
# 💧 IRRIGATION FLOW (pump instability realism)
# =========================
def irrigation_flow():
    if not valve:
        return 0
    return random.uniform(3.0, MAX_FLOW)

# =========================
# 🌱 PLANT UPTAKE (root zone drain)
# =========================
def plant_uptake():
    global plant_health
    base = ROOT_UPTAKE * (plant_health / 100)
    return base + random.uniform(0.2, 0.6)

# =========================
# 🌿 SOIL PHYSICS ENGINE
# =========================
def simulate_soil():
    global plant_health

    flow = irrigation_flow()
    uptake = plant_uptake()
    evap = evaporation()

    # surface evaporation
    soil.top += evap - (soil.top * DIFFUSION)

    # diffusion chain
    soil.mid += (soil.top - soil.mid) * DIFFUSION
    soil.deep += (soil.mid - soil.deep) * DIFFUSION

    # irrigation input
    soil.top += flow

    # plant consumption
    soil.mid -= uptake

    # deep drainage loss
    soil.deep -= max(0, soil.deep - 780) * 0.02

    # clamp realism bounds
    soil.top = max(SOIL_MIN, min(SOIL_MAX, soil.top))
    soil.mid = max(SOIL_MIN, min(SOIL_MAX, soil.mid))
    soil.deep = max(SOIL_MIN, min(SOIL_MAX, soil.deep))

    avg = soil.avg()

    # plant health model
    if 480 <= avg <= 580:
        plant_health += 0.04
    elif avg > 750 or avg < 320:
        plant_health -= 0.10
    else:
        plant_health -= 0.02

    plant_health = max(0, min(100, plant_health))

    return avg

# =========================
# 🎛️ CONTROL (simple proportional ESP32 logic)
# =========================
def compute_flow(avg):
    error = avg - IDEAL_SOIL

    if abs(error) < 20:
        return 0

    flow = error * 0.03
    return max(0, min(MAX_FLOW, flow))

# =========================
# 🌊 VALVE CONTROL (hysteresis + anti-chatter)
# =========================
def update_valve(avg):
    global valve, last_switch

    now = time.time()

    if now - last_switch < MIN_SWITCH:
        return

    flow = compute_flow(avg)

    if valve and avg < WATER_OFF:
        valve = False
        last_switch = now

    elif not valve and avg > WATER_ON and flow > 1.0:
        valve = True
        last_switch = now

# =========================
# 📡 SEND DATA
# =========================
def send(avg):
    sensors = [read_sensor(avg) for _ in range(5)]

    payload = {
        "bed_id": BED_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "sensors": sensors,
        "average": sum(sensors) / len(sensors),
        "valve_state": "ON" if valve else "OFF",
        "plant_health": plant_health,
        "weather": WEATHER
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

    print(f"{BED_ID} | soil:{avg:.1f} | valve:{valve} | health:{plant_health:.1f}")

# =========================
# 📡 HEARTBEAT
# =========================
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

# =========================
# 🔁 MAIN LOOP
# =========================
def loop():
    print("🌿 SINGLE ESP32 REALISTIC SIM STARTED")

    while True:
        WEATHER["temp"] += random.uniform(-0.15, 0.15)
        WEATHER["humidity"] += random.uniform(-0.5, 0.5)
        WEATHER["sun"] += random.uniform(-0.03, 0.03)

        WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
        WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

        avg = simulate_soil()
        update_valve(avg)
        send(avg)

        time.sleep(2)

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    threading.Thread(target=heartbeat, daemon=True).start()
    loop()
import requests
import random
import time
from datetime import datetime, timedelta
import threading
import os
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
# 🌱 PHYSICAL CONSTANTS
# =========================================================

SOIL_DRY = 850
SOIL_WET = 250
IDEAL_SOIL = 520

WATER_ON_THRESHOLD = 560
WATER_OFF_THRESHOLD = 500

MIN_SWITCH_TIME = 8

DEADZONE = 25
MAX_WATER_TIME = 6

Kp, Ki, Kd = 0.18, 0.001, 0.04
INTEGRAL_CLAMP = 800


# =========================================================
# 🌦️ WEATHER (local environment model)
# =========================================================

WEATHER = {
    "temp": 22.0,
    "humidity": 50.0,
    "sun": 0.5,
    "rain": False
}


# =========================================================
# 🌿 DEVICE STATE (ESP32 RAM equivalent)
# =========================================================

class Bed:
    def __init__(self, bed_id):
        self.id = bed_id
        self.soil = random.uniform(500, 650)
        self.rssi = random.uniform(-65, -45)
        self.health = 70.0

        self.valve = False

        self.integral = 0.0
        self.last_error = 0.0

        self.water_buffer = 0.0

        self.last_switch = datetime.utcnow()


bed = Bed(BED_ID)


# =========================================================
# 🌦️ WEATHER UPDATE
# =========================================================

def update_weather():
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["temp"] = max(-5, min(40, WEATHER["temp"]))
    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))


# =========================================================
# 🌱 SENSOR
# =========================================================

def read_soil():
    return bed.soil + random.uniform(-3, 3)


# =========================================================
# 🎛️ PID CONTROL
# =========================================================

def compute_watering_time():
    error = bed.soil - IDEAL_SOIL

    if abs(error) < DEADZONE:
        return 0

    if bed.soil < IDEAL_SOIL:
        return 0

    bed.integral += error
    bed.integral = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, bed.integral))

    derivative = error - bed.last_error
    bed.last_error = error

    control = (Kp * error) + (Ki * bed.integral) + (Kd * derivative)

    return max(0, min(MAX_WATER_TIME, control))


# =========================================================
# 🌊 VALVE CONTROL
# =========================================================

def apply_valve_control():
    now = datetime.utcnow()

    if (now - bed.last_switch).total_seconds() < MIN_SWITCH_TIME:
        return

    # OFF
    if bed.valve and bed.soil < WATER_OFF_THRESHOLD:
        bed.valve = False
        bed.last_switch = now
        return

    # ON
    if not bed.valve and bed.soil > WATER_ON_THRESHOLD:
        duration = compute_watering_time()
        if duration > 0:
            bed.valve = True
            bed.last_switch = now


# =========================================================
# 🌿 PHYSICS SIMULATION
# =========================================================

def simulate():
    evap = (
        max(0, WEATHER["temp"] - 18) * 0.3 +
        WEATHER["sun"] * 0.9 +
        (100 - WEATHER["humidity"]) * 0.1
    ) * 0.25

    bed.soil += evap

    if WEATHER["rain"]:
        bed.soil -= random.uniform(3, 8)

    if bed.valve:
        bed.water_buffer += 6

    absorbed = bed.water_buffer * 0.35
    bed.soil -= absorbed
    bed.water_buffer -= absorbed

    bed.soil = max(SOIL_WET, min(SOIL_DRY, bed.soil))

    # plant health
    if 470 <= bed.soil <= 580:
        bed.health += 0.05
    elif bed.soil > 780 or bed.soil < 330:
        bed.health -= 0.08
    else:
        bed.health -= 0.015

    bed.health = max(0, min(100, bed.health))

    # RSSI drift
    bed.rssi += random.uniform(-1, 1)
    if bed.valve:
        bed.rssi -= random.uniform(0.5, 1.5)

    bed.rssi = max(-90, min(-30, bed.rssi))


# =========================================================
# 📡 SEND TELEMETRY
# =========================================================

def send():
    sensors = [bed.soil + random.uniform(-3, 3) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    payload = {
        "bed_id": bed.id,
        "timestamp": datetime.utcnow().isoformat(),
        "sensors": sensors,
        "average": avg,
        "valve_state": "ON" if bed.valve else "OFF",
        "plant_health": bed.health,
        "weather": WEATHER,
        "rssi": int(bed.rssi)
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

    print(
        f"{bed.id} | soil:{avg:.0f} | "
        f"valve:{bed.valve} | "
        f"health:{bed.health:.1f}"
    )


# =========================================================
# 📡 HEARTBEAT THREAD
# =========================================================

def heartbeat():
    while True:
        try:
            requests.post(
                f"{SERVER}/api/node/heartbeat",
                params={"bed_id": bed.id},
                headers=HEADERS,
                timeout=2
            )
        except:
            pass

        time.sleep(10)


# =========================================================
# 🔁 MAIN LOOP (ESP32 loop())
# =========================================================

def loop():
    print("🌿 SINGLE BED ESP32 SIM RUNNING")

    while True:
        update_weather()

        bed.soil = read_soil()

        simulate()
        apply_valve_control()
        send()

        time.sleep(2)


# =========================================================
# 🚀 SETUP
# =========================================================

def setup():
    print("booting ESP32 device...")
    print(f"node: {bed.id}")

    threading.Thread(target=heartbeat, daemon=True).start()


# =========================================================
# ▶ START
# =========================================================

if __name__ == "__main__":
    setup()
    loop()
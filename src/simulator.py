import requests
import random
import time
import os
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

# =========================
# 🌐 CONFIG
# =========================
SERVER = "http://127.0.0.1:8000"

load_dotenv()
API_KEY = os.getenv("GARDEN_API_KEY")
HEADERS = {"x-api-key": API_KEY}

BEDS = [f"bed_{i}" for i in range(1, 5)]

# =========================
# 🌱 SOIL MODEL
# =========================
SOIL_DRY = 850
SOIL_WET = 250
IDEAL_SOIL = 520

SOIL_TYPES = {
    "bed_1": {"drain": 1.3, "retain": 0.85},
    "bed_2": {"drain": 1.0, "retain": 1.0},
    "bed_3": {"drain": 0.7, "retain": 1.2},
    "bed_4": {"drain": 1.1, "retain": 0.95},
}

# =========================
# 🎛️ PID
# =========================
Kp, Ki, Kd = 0.28, 0.003, 0.05
INTEGRAL_CLAMP = 600
CONTROL_CLAMP = 3.2

# =========================
# 🌦️ WEATHER
# =========================
WEATHER = {
    "temp": 22,
    "humidity": 50,
    "rain": False,
    "sun": 0.5,
}

# =========================
# 🌱 STATE
# =========================
soil_state = {b: random.uniform(500, 650) for b in BEDS}
plant_health = {b: 70.0 for b in BEDS}
watering_until = {b: None for b in BEDS}
water_buffer = {b: 0.0 for b in BEDS}

integral = {b: 0.0 for b in BEDS}
last_error = {b: 0.0 for b in BEDS}

# =========================
# 💓 HEARTBEAT (ALWAYS RUNNING)
# =========================
def heartbeat_loop():
    while True:
        for bed in BEDS:
            try:
                requests.post(
                    f"{SERVER}/api/node/heartbeat",
                    params={"bed_id": bed},
                    headers=HEADERS,
                    timeout=2
                )
            except:
                pass
        time.sleep(10)

# =========================
# 🌦️ WEATHER UPDATE
# =========================
def update_weather():
    try:
        r = requests.get(f"{SERVER}/api/weather/current", headers=HEADERS, timeout=3)
        d = r.json()
        WEATHER.update(d)
    except:
        pass

    # small natural drift
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================
# 🌿 PHYSICS SIMULATION
# =========================
def simulate(bed):
    soil = soil_state[bed]
    now = datetime.utcnow()
    soil_type = SOIL_TYPES[bed]

    # 🌞 evaporation
    evap = (
        max(0, WEATHER["temp"] - 18) * 0.3 +
        WEATHER["sun"] * 0.9 +
        (100 - WEATHER["humidity"]) * 0.1
    ) * 0.25

    evap *= soil_type["drain"]
    soil += evap

    # 🌱 plant uptake
    soil += 0.1 * (plant_health[bed] / 100)

    # 🌧️ rain
    if WEATHER["rain"]:
        soil -= random.uniform(3, 8)

    # 💧 watering buffer
    if watering_until[bed] and now < watering_until[bed]:
        water_buffer[bed] += 6

    absorbed = water_buffer[bed] * 0.3
    soil -= absorbed
    water_buffer[bed] -= absorbed

    # 🎛️ PID
    error = soil - IDEAL_SOIL

    integral[bed] += error
    integral[bed] = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, integral[bed]))

    derivative = error - last_error[bed]
    last_error[bed] = error

    control = Kp * error + Ki * integral[bed] + Kd * derivative
    control = max(-CONTROL_CLAMP, min(CONTROL_CLAMP, control))

    soil -= control

    # 🌿 soil physics stability
    soil *= soil_type["retain"]

    # smoothing (prevents jitter)
    soil_state[bed] += (soil - soil_state[bed]) * 0.5

    # noise
    soil_state[bed] += random.uniform(-0.5, 0.5)

    soil_state[bed] = max(SOIL_WET, min(SOIL_DRY, soil_state[bed]))

    # 🌱 plant health
    s = soil_state[bed]
    if 470 <= s <= 580:
        plant_health[bed] += 0.04
    elif s > 780 or s < 330:
        plant_health[bed] -= 0.07
    else:
        plant_health[bed] -= 0.01

    plant_health[bed] = max(0, min(100, plant_health[bed]))

# =========================
# 🚰 WATER DECISION
# =========================
def check_water(bed):
    try:
        r = requests.post(
            f"{SERVER}/api/should-water",
            params={"bed_id": bed, "average_moisture": soil_state[bed]},
            headers=HEADERS,
            timeout=3
        )
        return r.json()
    except:
        return None

def apply_watering(bed, decision):
    if decision and decision.get("water"):
        watering_until[bed] = datetime.utcnow() + timedelta(seconds=6)

# =========================
# 📡 SEND DATA
# =========================
def send(bed):
    sensors = [soil_state[bed] + random.uniform(-3, 3) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    decision = check_water(bed)
    apply_watering(bed, decision)

    valve = "ON" if watering_until[bed] and datetime.utcnow() < watering_until[bed] else "OFF"

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json={
                "bed_id": bed,
                "timestamp": datetime.utcnow().isoformat(),
                "sensors": sensors,
                "average": avg,
                "valve_state": valve,
                "plant_health": plant_health[bed],
                "weather": WEATHER
            },
            headers=HEADERS,
            timeout=3
        )
    except:
        pass

    print(f"{bed} | ADC {avg:.0f} | VALVE {valve} | health:{plant_health[bed]:.1f}")

# =========================
# 🔁 MAIN LOOP
# =========================
def run():
    print("🌿 FIXED living ecosystem running...")

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    while True:
        update_weather()

        for bed in BEDS:
            try:
                simulate(bed)
                send(bed)
            except Exception as e:
                print("❌ ERROR:", bed, e)

        time.sleep(2)

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    run()
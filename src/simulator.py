import requests
import random
import time
import os
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
# 🌱 SOIL MODEL (ADC)
# =========================
SOIL_DRY = 850
SOIL_WET = 250
IDEAL_SOIL = 520

# =========================
# 🌱 SOIL TYPES
# =========================
SOIL_TYPES = {
    "bed_1": {"drain": 1.3, "retain": 0.85},  # sandy
    "bed_2": {"drain": 1.0, "retain": 1.0},   # loam
    "bed_3": {"drain": 0.7, "retain": 1.2},   # clay
    "bed_4": {"drain": 1.1, "retain": 0.95},
}

# =========================
# 🎛️ PID CONTROL
# =========================
Kp = 0.28
Ki = 0.003
Kd = 0.05

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
soil_state = {bed: random.uniform(500, 650) for bed in BEDS}
plant_health = {bed: 70.0 for bed in BEDS}
watering_until = {bed: None for bed in BEDS}
water_buffer = {bed: 0.0 for bed in BEDS}

integral_error = {bed: 0.0 for bed in BEDS}
last_error = {bed: 0.0 for bed in BEDS}

# =========================
# 🌦️ WEATHER UPDATE
# =========================
def update_weather():
    try:
        r = requests.get(f"{SERVER}/api/weather/current", headers=HEADERS, timeout=5)
        d = r.json()

        WEATHER["temp"] = d["temp"]
        WEATHER["humidity"] = d["humidity"]
        WEATHER["rain"] = d["is_raining_now"]
        WEATHER["sun"] = d["sun"]
    except:
        pass

    # 🌙 day/night effect
    hour = datetime.utcnow().hour
    if 6 <= hour <= 18:
        WEATHER["sun"] *= 1.1
    else:
        WEATHER["sun"] *= 0.3

    # 🌬️ small drift
    WEATHER["temp"] += random.uniform(-0.3, 0.3)
    WEATHER["humidity"] += random.uniform(-1, 1)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================
# 🌿 SIMULATION CORE
# =========================
def simulate(bed):
    now = datetime.utcnow()
    soil = soil_state[bed]
    soil_type = SOIL_TYPES[bed]

    # 🌞 evaporation (affected by soil type)
    evap = (
        max(0, WEATHER["temp"] - 18) * 0.35 +
        WEATHER["sun"] * 1.0 +
        (100 - WEATHER["humidity"]) * 0.12
    ) * 0.22

    evap *= soil_type["drain"]
    soil += evap

    # 🌱 plant uptake (plants drink water)
    uptake = 0.15 * (plant_health[bed] / 100)
    soil += uptake

    # 🌧️ rain
    if WEATHER["rain"]:
        soil -= random.uniform(4, 10)

    # 💧 irrigation → goes into buffer first
    if watering_until[bed] and now < watering_until[bed]:
        water_buffer[bed] += 8

    # 💧 buffer slowly absorbed
    absorbed = water_buffer[bed] * 0.3
    soil -= absorbed
    water_buffer[bed] -= absorbed

    # 🎛️ PID
    error = soil - IDEAL_SOIL

    integral_error[bed] += error
    integral_error[bed] = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, integral_error[bed]))

    derivative = error - last_error[bed]
    last_error[bed] = error

    control = (
        Kp * error +
        Ki * integral_error[bed] +
        Kd * derivative
    )

    control = max(-CONTROL_CLAMP, min(CONTROL_CLAMP, control))

    soil -= control

    # 🌱 soil retention behavior
    soil *= soil_type["retain"]

    # 🌿 inertia (smooth but alive)
    soil_state[bed] += (soil - soil_state[bed]) * 0.6

    # 🎲 noise
    soil_state[bed] += random.uniform(-1, 1)

    # clamp
    soil_state[bed] = max(SOIL_WET, min(SOIL_DRY, soil_state[bed]))

    # 🌿 plant health
    s = soil_state[bed]
    if 470 <= s <= 580:
        plant_health[bed] += 0.05
    elif s > 780 or s < 330:
        plant_health[bed] -= 0.08
    else:
        plant_health[bed] -= 0.015

    plant_health[bed] = max(0, min(100, plant_health[bed]))

    sensors = [soil_state[bed] + random.uniform(-4, 4) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    return sensors, avg

# =========================
# 🚰 WATERING
# =========================
def apply_watering(bed, decision):
    now = datetime.utcnow()
    if decision and decision.get("water"):
        watering_until[bed] = now + timedelta(seconds=6)

# =========================
# 🤖 API DECISION
# =========================
def check(bed, avg):
    try:
        r = requests.post(
            f"{SERVER}/api/should-water",
            params={"bed_id": bed, "average_moisture": avg},
            headers=HEADERS,
            timeout=5
        )
        return r.json()
    except:
        return None

# =========================
# 📡 SEND DATA
# =========================
def send(bed, sensors, avg, valve):
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
            timeout=5
        )
    except:
        pass

# =========================
# 🔁 LOOP
# =========================
def run():
    print("🌿 living ecosystem sim running...")

    while True:
        print("-" * 60)
        update_weather()

        for bed in BEDS:
            sensors, avg = simulate(bed)

            decision = check(bed, avg)
            apply_watering(bed, decision)

            now = datetime.utcnow()
            valve = "ON" if watering_until[bed] and now < watering_until[bed] else "OFF"

            send(bed, sensors, avg, valve)

            print(
                f"{bed} | ADC {avg:.0f} | {valve} | "
                f"health:{plant_health[bed]:.1f} | "
                f"{'🌧️' if WEATHER['rain'] else '☀️'}"
            )
        print("-" * 60)
        time.sleep(60)
       

if __name__ == "__main__":
    run()
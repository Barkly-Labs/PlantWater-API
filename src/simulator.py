import requests
import random
import time
import threading
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
# 🌱 REALISTIC SOIL (ADC VALUES)
# =========================
SOIL_DRY = 850
SOIL_WET = 250
IDEAL_SOIL = 520

# =========================
# 🎛️ STABLE PID GAINS
# =========================
Kp = 0.22
Ki = 0.004
Kd = 0.06

INTEGRAL_CLAMP = 800
CONTROL_CLAMP = 3.0

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

watering_state = {bed: None for bed in BEDS}

integral_error = {bed: 0.0 for bed in BEDS}
last_error = {bed: 0.0 for bed in BEDS}

# =========================
# 🌦️ WEATHER (SAFE FAIL)
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

# =========================
# 🌿 SIMULATION CORE
# =========================
def simulate_sensor(bed):
    soil = soil_state[bed]
    now = datetime.utcnow()

    # -------------------------
    # 🌞 evaporation (SOFTENED A LOT)
    # -------------------------
    evap = (
        max(0, WEATHER["temp"] - 18) * 0.4 +
        WEATHER["sun"] * 1.2 +
        (100 - WEATHER["humidity"]) * 0.15
    ) * 0.15  # IMPORTANT damping

    soil += evap  # dries (higher = drier)

    # -------------------------
    # 🌧️ rain
    # -------------------------
    if WEATHER["rain"]:
        soil -= random.uniform(2, 6)

    # -------------------------
    # 💧 watering
    # -------------------------
    if watering_state[bed] and now < watering_state[bed]:
        soil -= 6

    # -------------------------
    # 🎯 PID (stable + anti-runaway)
    # -------------------------
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

    soil -= control  # watering effect

    # -------------------------
    # 🌿 smoothing (prevents runaway drift)
    # -------------------------
    soil = soil_state[bed] * 0.8 + soil * 0.2

    # -------------------------
    # 📉 noise (tiny only)
    # -------------------------
    soil += random.uniform(-1, 1)

    # clamp
    soil = max(SOIL_WET, min(SOIL_DRY, soil))
    soil_state[bed] = soil

    # -------------------------
    # 🌱 health model (stable)
    # -------------------------
    if 450 <= soil <= 600:
        plant_health[bed] += 0.05
    elif soil > 780:
        plant_health[bed] -= 0.08
    elif soil < 320:
        plant_health[bed] -= 0.08
    else:
        plant_health[bed] -= 0.01

    plant_health[bed] = max(0, min(100, plant_health[bed]))

    sensors = [soil + random.uniform(-5, 5) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    return sensors, avg

# =========================
# 🚰 watering trigger
# =========================
def apply_watering(bed, decision):
    now = datetime.utcnow()

    if decision and decision.get("water"):
        watering_state[bed] = now + timedelta(seconds=6)

# =========================
# 🤖 decision
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
# 📡 send
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
    print("🌿 stable soil sim running...")

    while True:
        update_weather()

        for bed in BEDS:
            sensors, avg = simulate_sensor(bed)

            decision = check(bed, avg)
            apply_watering(bed, decision)

            now = datetime.utcnow()
            valve = "ON" if watering_state[bed] and now < watering_state[bed] else "OFF"

            send(bed, sensors, avg, valve)

            print(
                f"{bed} | {avg:.0f} | {valve} | "
                f"health:{plant_health[bed]:.1f} | "
                f"{'🌧️' if WEATHER['rain'] else '☀️'}"
            )

        time.sleep(2)

if __name__ == "__main__":
    run()
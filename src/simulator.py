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

if not API_KEY:
    raise ValueError("Missing GARDEN_API_KEY in .env")

HEADERS = {"x-api-key": API_KEY}

BEDS = [f"bed_{i}" for i in range(1, 5)]

# =========================
# 🌱 REAL-WORLD SCALE SYSTEM
# =========================
IDEAL_MOISTURE = 55.0  # %
MOISTURE_MIN = 0.0
MOISTURE_MAX = 100.0

# 🎛️ PID (tuned for % system)
Kp = 0.25
Ki = 0.005
Kd = 0.08

INTEGRAL_CLAMP = 2000
CONTROL_CLAMP = 5.0  # % change per tick max

# =========================
# 🌦️ WEATHER
# =========================
WEATHER = {
    "temp": 22,
    "humidity": 50,
    "rain": False,
    "sun": 0.5,
    "clouds": 0
}

# =========================
# 🌱 STATE
# =========================
soil_state = {bed: random.uniform(45, 65) for bed in BEDS}
plant_health = {bed: 70.0 for bed in BEDS}

watering_state = {bed: None for bed in BEDS}

integral_error = {bed: 0.0 for bed in BEDS}
last_error = {bed: 0.0 for bed in BEDS}

# =========================
# 🌦️ WEATHER FETCH
# =========================
def update_weather():
    try:
        r = requests.get(
            f"{SERVER}/api/weather/current",
            headers=HEADERS,
            timeout=5
        )
        data = r.json()

        WEATHER["temp"] = data["temp"]
        WEATHER["humidity"] = data["humidity"]
        WEATHER["rain"] = data["is_raining_now"]
        WEATHER["sun"] = data["sun"]
        WEATHER["clouds"] = data.get("clouds", 0)

    except:
        pass

# =========================
# 🫀 HEARTBEAT
# =========================
def send_heartbeat(bed_id):
    try:
        requests.post(
            f"{SERVER}/api/node/heartbeat",
            params={"bed_id": bed_id},
            headers=HEADERS,
            timeout=3
        )
    except:
        pass
IDEAL_SOIL = 500
SOIL_DRY = 850     # air / very dry soil
SOIL_WET = 250   

# =========================
# 🌿 REALISTIC SOIL MODEL
# =========================
def simulate_sensor(bed_id):
  
    soil = soil_state[bed_id]
    now = datetime.utcnow()

    # -------------------------
    # 🌞 DRYING (higher number = drier)
    # -------------------------
    heat_factor = max(0, (WEATHER["temp"] - 15)) * 0.8
    sun_factor = WEATHER["sun"] * 2.5
    humidity_factor = (100 - WEATHER["humidity"]) * 0.3

    evaporation = heat_factor + sun_factor + humidity_factor

    soil += evaporation  # DRY → value increases

    # -------------------------
    # 🌧️ RAIN (wets soil → value decreases)
    # -------------------------
    if WEATHER["rain"]:
        soil -= random.uniform(5, 15)

    # -------------------------
    # 💧 WATERING (strong wetting effect)
    # -------------------------
    if watering_state[bed_id] and now < watering_state[bed_id]:
        soil -= 8  # strong wetting per tick

    # -------------------------
    # 🎯 PID CONTROLLER (now inverted!)
    # -------------------------
    error = soil - IDEAL_SOIL  # reversed logic

    integral_error[bed_id] += error
    integral_error[bed_id] = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, integral_error[bed_id]))

    derivative = error - last_error[bed_id]
    last_error[bed_id] = error

    control = (
        Kp * error +
        Ki * integral_error[bed_id] +
        Kd * derivative
    )

    control = max(-CONTROL_CLAMP, min(CONTROL_CLAMP, control))

    soil -= control  # IMPORTANT: watering reduces value

    # -------------------------
    # 🌿 NATURAL DRIFT
    # -------------------------
    soil += (IDEAL_SOIL - soil) * 0.01

    # -------------------------
    # 📉 NOISE (realistic sensor jitter)
    # -------------------------
    soil += random.uniform(-2, 2)

    # clamp to real sensor limits
    soil = max(SOIL_WET, min(SOIL_DRY, soil))
    soil_state[bed_id] = soil

    sensors = [soil + random.uniform(-10, 10) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    # =========================
    # 🌿 PLANT HEALTH (updated logic)
    # =========================
    if 450 <= soil <= 600:
        plant_health[bed_id] += 0.08
    elif soil > 780:   # too dry
        plant_health[bed_id] -= 0.12
    elif soil < 300:   # too wet
        plant_health[bed_id] -= 0.1
    else:
        plant_health[bed_id] -= 0.02

    plant_health[bed_id] = max(0, min(100, plant_health[bed_id]))

    return sensors, avg

# =========================
# 🚰 WATERING LOGIC
# =========================
def apply_watering_effect(bed_id, decision):
    now = datetime.utcnow()

    if decision and decision.get("water"):
        duration = 6  # longer, realistic irrigation
        watering_state[bed_id] = now + timedelta(seconds=duration)

        plant_health[bed_id] = min(100, plant_health[bed_id] + 1.5)

        def stop():
            time.sleep(duration)
            print(f"💧 STOP {bed_id}")

        threading.Thread(target=stop, daemon=True).start()

        print(f"💧 WATER {bed_id}")

# =========================
# 🤖 DECISION SYSTEM
# =========================
def check_watering(bed_id, avg):
    try:
        r = requests.post(
            f"{SERVER}/api/should-water",
            params={"bed_id": bed_id, "average_moisture": avg},
            headers=HEADERS,
            timeout=5
        )
        return r.json()
    except:
        return None

# =========================
# 📡 SEND DATA
# =========================
def send_data(bed_id, sensors, avg, valve_state):
    payload = {
        "bed_id": bed_id,
        "timestamp": datetime.utcnow().isoformat(),
        "sensors": sensors,
        "average": avg,
        "valve_state": valve_state,
        "plant_health": plant_health[bed_id],
        "weather": WEATHER
    }

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json=payload,
            headers=HEADERS,
            timeout=5
        )
    except:
        pass

# =========================
# 🔁 MAIN LOOP
# =========================
def run():
    print("🌿 Real-World Scale Ecosystem running...")

    while True:
        update_weather()

        for bed in BEDS:

            send_heartbeat(bed)

            sensors, avg = simulate_sensor(bed)

            decision = check_watering(bed, avg)

            apply_watering_effect(bed, decision)

            now = datetime.utcnow()
            valve = "ON" if watering_state[bed] and now < watering_state[bed] else "OFF"

            send_data(bed, sensors, avg, valve)

            print(
                f"{bed} | "
                f"{avg:.1f}% | "
                f"{valve} | "
                f"plant:{plant_health[bed]:.1f} | "
                f"{WEATHER['temp']:.1f}°C | "
                f"{WEATHER['humidity']:.0f}% | "
                f"{'🌧️' if WEATHER['rain'] else '☀️'}"
            )

        time.sleep(2)


if __name__ == "__main__":
    run()
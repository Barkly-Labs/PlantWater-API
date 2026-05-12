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
# 🌦️ WEATHER STATE
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
soil_state = {bed: random.uniform(480, 560) for bed in BEDS}
watering_state = {bed: None for bed in BEDS}
override_state = {bed: None for bed in BEDS}

plant_health = {bed: 70.0 for bed in BEDS}

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

# =========================
# 🌱 SENSOR SIMULATION (STABLE SYSTEM)
# =========================
def simulate_sensor(bed_id):
    base = soil_state[bed_id]
    now = datetime.utcnow()

    # 🌿 memory smoothing
    base = (soil_state[bed_id] * 0.75) + (base * 0.25)

    # 🎯 equilibrium pull (keeps system alive)
    ideal = 520
    base += (ideal - base) * 0.06

    # 🌦️ environmental drying
    heat = max(0, (WEATHER["temp"] - 10) / 20)
    sun = WEATHER["sun"]
    humidity = (100 - WEATHER["humidity"]) / 100

    dry = (
        0.6 +
        heat * 1.8 +
        sun * 1.4 +
        humidity * 1.0
    )

    base -= dry

    # 🌧️ rain (soft, not destructive)
    if WEATHER["rain"]:
        base += random.uniform(0.5, 2.0)

    # 💧 watering (controlled pulse, not flood)
    if watering_state[bed_id] and now < watering_state[bed_id]:
        base += random.uniform(8.0, 14.0)

    # 🌿 drainage (THIS is what fixes “wet death”)
    base -= (base - 520) * 0.03

    # 📉 noise
    base += random.uniform(-2, 2)

    # clamp soil
    base = max(120, min(900, base))

    soil_state[bed_id] = base

    sensors = [base + random.uniform(-5, 5) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    # =========================
    # 🌿 PLANT HEALTH (BALANCED MODEL)
    # =========================
    if 340 <= base <= 600:
        plant_health[bed_id] += 0.10  # ideal zone

    elif 260 <= base < 340:
        plant_health[bed_id] -= 0.04  # slightly dry

    elif 600 < base <= 720:
        plant_health[bed_id] -= 0.04  # slightly wet

    elif base < 260:
        plant_health[bed_id] -= 0.08  # drought

    elif base > 720:
        plant_health[bed_id] -= 0.08  # flooding

    # recovery buffer
    if 340 <= base <= 600 and plant_health[bed_id] < 50:
        plant_health[bed_id] += 0.12

    plant_health[bed_id] = max(0, min(100, plant_health[bed_id]))

    return sensors, avg

# =========================
# 🚰 WATERING LOGIC
# =========================
def apply_watering_effect(bed_id, decision, override=None):
    now = datetime.utcnow()

    if override in ["ON", "OFF"]:
        watering_state[bed_id] = now + timedelta(seconds=999999) if override == "ON" else None
        return

    if decision and decision.get("water"):
        duration = 3
        watering_state[bed_id] = now + timedelta(seconds=duration)

        plant_health[bed_id] = min(100, plant_health[bed_id] + 2.0)

        def stop():
            time.sleep(duration)
            print(f"💧 STOP {bed_id}")

        threading.Thread(target=stop, daemon=True).start()

        print(f"💧 WATER {bed_id}")

# =========================
# 🤖 WATER DECISION
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
def send_data(bed_id, sensors, avg, valve_state, override=False):
    payload = {
        "bed_id": bed_id,
        "timestamp": datetime.utcnow().isoformat(),
        "sensors": [float(x) for x in sensors],
        "average": float(avg),
        "valve_state": valve_state,
        "override_active": override,
        "rssi": random.randint(-90, -40),
        "battery": round(random.uniform(3.6, 4.2), 2),
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
    print("🌿 Stable Ecosystem Simulator running...")

    while True:
        update_weather()

        for bed in BEDS:

            send_heartbeat(bed)

            sensors, avg = simulate_sensor(bed)

            decision = check_watering(bed, avg)

            override = override_state.get(bed)

            apply_watering_effect(bed, decision, override)

            now = datetime.utcnow()
            valve = "ON" if watering_state[bed] and now < watering_state[bed] else "OFF"

            send_data(bed, sensors, avg, valve, override is not None)

            print(
                f"{bed} | "
                f"{avg:.1f} | "
                f"{valve} | "
                f"plant:{plant_health[bed]:.1f} | "
                f"{WEATHER['temp']:.1f}°C | "
                f"{WEATHER['humidity']:.0f}% | "
                f"{'🌧️' if WEATHER['rain'] else '☀️'}"
            )

        time.sleep(2)


if __name__ == "__main__":
    run()
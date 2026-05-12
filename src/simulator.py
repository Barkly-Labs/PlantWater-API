import requests
import random
import time
import threading
from datetime import datetime, timedelta

# =========================
# 🌐 CONFIG
# =========================
SERVER = "http://127.0.0.1:8000"
API_KEY = "your_super_secret_key"
HEADERS = {"x-api-key": API_KEY}

BEDS = [f"bed_{i}" for i in range(1, 5)]

# =========================
# 🌦️ WEATHER STATE (FROM API)
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
soil_state = {bed: random.uniform(600, 800) for bed in BEDS}
watering_state = {bed: None for bed in BEDS}
override_state = {bed: None for bed in BEDS}

plant_health = {bed: 70.0 for bed in BEDS}
last_water_time = {bed: None for bed in BEDS}


# =========================
# 🌦️ WEATHER FETCH (YOUR API)
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

    except Exception as e:
        print("weather fetch failed:", e)

        # fallback (so sim never dies)
        WEATHER["temp"] += random.uniform(-0.2, 0.2)
        WEATHER["humidity"] += random.uniform(-1, 1)


# =========================
# 🫀 HEARTBEAT
# =========================
def send_heartbeat(bed_id):
    try:
        requests.post(
            f"{SERVER}/api/node/heartbeat",
            params={"bed_id": bed_id},
            headers=HEADERS
        )
    except Exception as e:
        print("heartbeat failed:", e)


# =========================
# 🌱 SENSOR SIMULATION
# =========================
def simulate_sensor(bed_id):
    base = soil_state[bed_id]
    now = datetime.utcnow()

    # 🌦️ WEATHER-DRIVEN DRYING MODEL
    heat_factor = max(0, (WEATHER["temp"] - 10) / 20)
    sun_factor = WEATHER["sun"]
    humidity_factor = (100 - WEATHER["humidity"]) / 100

    dry_rate = 0.5 + (heat_factor * 2.5) + (sun_factor * 2) + (humidity_factor * 2)

    base -= dry_rate

    # 🌧️ rain adds moisture
    if WEATHER["rain"]:
        base += random.uniform(5, 15)

    # 💧 watering system
    if watering_state[bed_id] and now < watering_state[bed_id]:
        base += random.uniform(5, 12)

    # 🌿 plant health logic
    if base > 750:
        plant_health[bed_id] -= 0.25
    elif base < 300:
        plant_health[bed_id] -= 0.1
    else:
        plant_health[bed_id] += 0.05

    plant_health[bed_id] = max(0, min(100, plant_health[bed_id]))

    # noise
    value = base + random.uniform(-5, 5)
    value = max(200, min(850, value))

    soil_state[bed_id] = value

    sensors = [value + random.uniform(-12, 12) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

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

        plant_health[bed_id] = min(100, plant_health[bed_id] + 2.5)
        last_water_time[bed_id] = now

        def stop():
            time.sleep(duration)
            print(f"💧 STOP {bed_id}")

        threading.Thread(target=stop).start()

        print(f"💧 WATER {bed_id}")


# =========================
# 🤖 DECISION API CALL
# =========================
def check_watering(bed_id, avg):
    try:
        r = requests.post(
            f"{SERVER}/api/should-water",
            params={
                "bed_id": bed_id,
                "average_moisture": avg
            },
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

        # 🌦️ full weather snapshot
        "weather": WEATHER
    }

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json=payload,
            headers=HEADERS
        )
    except Exception as e:
        print("send failed:", e)


# =========================
# 🔁 MAIN LOOP
# =========================
def run():
    print("🌿 Weather-driven Smart Garden Simulator starting...")

    while True:

        # 🌦️ pull real weather first
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
                f"avg={avg:.1f} | "
                f"valve={valve} | "
                f"plant={plant_health[bed]:.1f} | "
                f"{WEATHER['temp']:.1f}°C | "
                f"{WEATHER['humidity']:.0f}% | "
                f"{'🌧️' if WEATHER['rain'] else '☀️'}"
            )

        time.sleep(2)


if __name__ == "__main__":
    run()
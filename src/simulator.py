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
# 🎛️ PID (STABLE)
# =========================
Kp, Ki, Kd = 0.18, 0.001, 0.04
INTEGRAL_CLAMP = 800
MAX_WATER_TIME = 6
DEADZONE = 25
COOLDOWN = 10

# =========================
# 🌊 VALVE STABILITY (NEW)
# =========================
WATER_ON_THRESHOLD = 560
WATER_OFF_THRESHOLD = 500
MIN_SWITCH_TIME = 8  # prevents relay chatter

valve_state = {b: False for b in BEDS}
last_switch_time = {b: datetime.utcnow() for b in BEDS}
watering_until = {b: None for b in BEDS}

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

water_buffer = {b: 0.0 for b in BEDS}

integral = {b: 0.0 for b in BEDS}
last_error = {b: 0.0 for b in BEDS}
rssi_state = {b: random.uniform(-65, -45) for b in BEDS}

# =========================
# 💓 HEARTBEAT
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
        WEATHER.update(r.json())
    except:
        pass

    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================
# 🌿 PHYSICS
# =========================
def simulate(bed):
    soil = soil_state[bed]
    now = datetime.utcnow()
    soil_type = SOIL_TYPES[bed]

    evap = (
        max(0, WEATHER["temp"] - 18) * 0.3 +
        WEATHER["sun"] * 0.9 +
        (100 - WEATHER["humidity"]) * 0.1
    ) * 0.25

    evap *= soil_type["drain"]
    soil += evap

    soil += 0.12 * (plant_health[bed] / 100)

    if WEATHER["rain"]:
        soil -= random.uniform(3, 8)

    # 💧 watering effect (from valve state, not timer chaos)
    if valve_state[bed]:
        water_buffer[bed] += 6

    absorbed = water_buffer[bed] * 0.35
    soil -= absorbed
    water_buffer[bed] -= absorbed

    soil *= soil_type["retain"]

    soil_state[bed] += (soil - soil_state[bed]) * 0.4
    soil_state[bed] += random.uniform(-0.5, 0.5)

    soil_state[bed] = max(SOIL_WET, min(SOIL_DRY, soil_state[bed]))

    s = soil_state[bed]
    if 470 <= s <= 580:
        plant_health[bed] += 0.05
    elif s > 780 or s < 330:
        plant_health[bed] -= 0.08
    else:
        plant_health[bed] -= 0.015

    rssi_state[bed] += random.uniform(-1, 1)

    if valve_state[bed]:
        rssi_state[bed] -= random.uniform(0.5, 1.5)

    rssi_state[bed] = max(-90, min(-30, rssi_state[bed]))
    plant_health[bed] = max(0, min(100, plant_health[bed]))

# =========================
# 🎛️ PID CONTROL (UNCHANGED CORE)
# =========================
def compute_watering_time(bed):
    soil = soil_state[bed]

    error = soil - IDEAL_SOIL

    if abs(error) < DEADZONE:
        return 0

    if soil < IDEAL_SOIL:
        return 0

    integral[bed] += error
    integral[bed] = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, integral[bed]))

    derivative = error - last_error[bed]
    last_error[bed] = error

    control = Kp * error + Ki * integral[bed] + Kd * derivative

    return max(0, min(MAX_WATER_TIME, control))

# =========================
# 🌊 STABLE VALVE CONTROL (FIXED)
# =========================
def apply_valve_control(bed):
    now = datetime.utcnow()
    soil = soil_state[bed]

    # 🧊 minimum switch protection
    if (now - last_switch_time[bed]).total_seconds() < MIN_SWITCH_TIME:
        return

    # 🌊 TURN OFF (only when clearly wet)
    if valve_state[bed] and soil < WATER_OFF_THRESHOLD:
        valve_state[bed] = False
        last_switch_time[bed] = now
        return

    # 🌵 TURN ON (only when clearly dry)
    if not valve_state[bed] and soil > WATER_ON_THRESHOLD:
        duration = compute_watering_time(bed)

        if duration > 0:
            valve_state[bed] = True
            last_switch_time[bed] = now
            watering_until[bed] = now + timedelta(seconds=duration)

# =========================
# 📡 SEND
# =========================
def send(bed):
    sensors = [soil_state[bed] + random.uniform(-3, 3) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    apply_valve_control(bed)

    valve = "ON" if valve_state[bed] else "OFF"

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
                "weather": WEATHER,
                "rssi": int(rssi_state[bed])
            },
            headers=HEADERS,
            timeout=3
        )
    except:
        pass

    print(f"{bed} | ADC {avg:.0f} | RSSI {rssi_state[bed]:.0f} dBm | VALVE {valve} | health:{plant_health[bed]:.1f}")

# =========================
# 🔁 MAIN
# =========================
def run():
    print("🌿 STABLE ecosystem running...")

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    while True:
        update_weather()

        for bed in BEDS:
            simulate(bed)
            send(bed)

        time.sleep(2)

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    run()
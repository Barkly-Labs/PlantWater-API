import requests
import random
import time
import threading
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# =========================================================
# 🌐 CONFIG
# =========================================================
SERVER = "http://127.0.0.1:8000"

load_dotenv()
API_KEY = os.getenv("GARDEN_API_KEY")
HEADERS = {"x-api-key": API_KEY}

BED_ID = "bed_1"

# =========================================================
# 🌱 SOIL MODEL
# =========================================================
SOIL_DRY = 850
SOIL_WET = 250
IDEAL_SOIL = 520

SOIL_TYPE = {"drain": 1.0, "retain": 1.0}

# =========================================================
# 🎛️ PID
# =========================================================
Kp, Ki, Kd = 0.18, 0.001, 0.04
INTEGRAL_CLAMP = 800
MAX_WATER_TIME = 6
DEADZONE = 25

# =========================================================
# 🌊 VALVE CONTROL
# =========================================================
WATER_ON_THRESHOLD = 560
WATER_OFF_THRESHOLD = 500
LOW_SOIL_RECOVERY = 440
MIN_SWITCH_TIME = 8

valve_state = False
last_switch_time = time.time()

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {
    "temp": 22,
    "humidity": 50,
    "rain": False,
    "sun": 0.5,
}

# =========================================================
# 🌱 STATE
# =========================================================
soil_state = random.uniform(500, 650)
plant_health = 70.0
soil_water = 0.0   # 💧 REAL SOIL WATER (IMPORTANT FIX)

integral = 0.0
last_error = 0.0
rssi_state = random.uniform(-65, -45)

# =========================================================
# 💓 HEARTBEAT
# =========================================================
def heartbeat_loop():
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
# 🌦️ WEATHER UPDATE
# =========================================================
def update_weather():
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🌿 PHYSICS ENGINE (FIXED REAL BALANCE)
# =========================================================
def simulate():
    global soil_state, plant_health, soil_water

    # =========================
    # 🌬️ EVAPORATION (NONLINEAR)
    # =========================
    dryness_factor = (soil_state - SOIL_WET) / (SOIL_DRY - SOIL_WET)
    dryness_factor = max(0, min(1, dryness_factor))

    evap = (
        max(0, WEATHER["temp"] - 18) * 0.22 +
        WEATHER["sun"] * 0.55 +
        (100 - WEATHER["humidity"]) * 0.06
    )

    evap *= (0.6 + 0.8 * dryness_factor)  # 🔥 key realism fix

    # =========================
    # 💧 WATER INPUT
    # =========================
    if valve_state:
        soil_water += 4.0

    # soil absorption is SLOW and saturating
    absorbed = soil_water * 0.18
    soil_water -= absorbed

    # =========================
    # 🌿 SOIL DYNAMICS
    # =========================
    soil_state += absorbed
    soil_state -= evap

    # natural diffusion (VERY small, no bias)
    soil_state += random.uniform(-0.3, 0.3)

    # =========================
    # 🌱 PLANT EFFECT
    # =========================
    uptake = 0.05 * (plant_health / 100)
    soil_state -= uptake

    # =========================
    # ❌ REMOVE EQUILIBRIUM BIAS
    # =========================
    # (intentionally removed — this was your drift bug)

    # =========================
    # CLAMP
    # =========================
    soil_state = max(SOIL_WET, min(SOIL_DRY, soil_state))

    # =========================
    # 🌱 PLANT HEALTH (SMOOTH)
    # =========================
    if 500 <= soil_state <= 560:
        plant_health += 0.03
    elif soil_state > 650 or soil_state < 400:
        plant_health -= 0.05
    else:
        plant_health -= 0.01

    plant_health = max(0, min(100, plant_health))

    return soil_state
# =========================================================
# 📡 SENSOR NOISE
# =========================================================
def read_sensor(value):
    return value + random.uniform(-3, 3)

# =========================================================
# 🎛️ PID CONTROLLER
# =========================================================
def compute_watering_time(soil):
    global integral, last_error

    error = soil - IDEAL_SOIL

    if abs(error) < DEADZONE:
        return 0

    if soil < IDEAL_SOIL:
        return 0

    integral += error
    integral = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, integral))

    derivative = error - last_error
    last_error = error

    control = Kp * error + Ki * integral + Kd * derivative

    return max(0, min(MAX_WATER_TIME, control))

# =========================================================
# 🌊 VALVE CONTROL (FIXED STABILITY)
# =========================================================
def apply_valve(soil):
    global valve_state, last_switch_time

    now = time.time()

    if now - last_switch_time < MIN_SWITCH_TIME:
        return

    # emergency dry rescue
    if soil < LOW_SOIL_RECOVERY:
        valve_state = True
        last_switch_time = now
        return

    # OFF
    if valve_state and soil < WATER_OFF_THRESHOLD:
        valve_state = False
        last_switch_time = now
        return

    # ON
    if not valve_state and soil > WATER_ON_THRESHOLD:
        if compute_watering_time(soil) > 0:
            valve_state = True
            last_switch_time = now

# =========================================================
# 📡 TELEMETRY
# =========================================================
def send(soil):
    sensors = [read_sensor(soil) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json={
                "bed_id": BED_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sensors": sensors,
                "average": avg,
                "valve_state": "ON" if valve_state else "OFF",
                "plant_health": plant_health,
                "rssi": int(rssi_state)
            },
            headers=HEADERS,
            timeout=3
        )
    except:
        pass

    print(f"ADC {avg:.0f} | SOIL {soil:.1f} | VALVE {valve_state} | HEALTH {plant_health:.1f}")

# =========================================================
# 🔁 MAIN LOOP
# =========================================================
def run():
    print("🌿 FINAL STABLE ESP32 SIM (REALISTIC SOIL HYDROLOGY) STARTED")

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    global soil_state

    while True:
        update_weather()

        soil = simulate()
        noisy = read_sensor(soil)

        apply_valve(noisy)
        send(noisy)

        time.sleep(2)

# =========================================================
# 🚀 START
# =========================================================
if __name__ == "__main__":
    run()
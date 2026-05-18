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
# 🌱 SOIL MODEL (0 = wet, 800 = dry)
# =========================================================
SOIL_DRY = 850
SOIL_WET = 250

SAFE_LOW = 400
SAFE_HIGH = 500
TARGET_SOIL = 470

FIELD_CAPACITY = 650

# =========================================================
# 🌊 HOSE / VALVE SYSTEM
# =========================================================
WATER_BUFFER_RATE = 9  # stronger hose burst

MIN_WATERING_TIME = 10.0
IRRIGATION_COOLDOWN = 25.0

valve_state = False
valve_command_time = 0

cycle_state = "IDLE"
cycle_start_time = 0
watering_start_soil = None

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {"temp": 22, "humidity": 50, "sun": 0.5}

def update_weather():
    WEATHER["temp"] += random.uniform(-0.25, 0.25)
    WEATHER["humidity"] += random.uniform(-0.9, 0.9)
    WEATHER["sun"] += random.uniform(-0.06, 0.06)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🧪 INJECTION SYSTEM (SPIKES)
# =========================================================
INJECT_SPIKE = False
INJECT_AMOUNT = 800.0
INJECT_DECAY = 0.88

# =========================================================
# 🌿 STATE
# =========================================================
soil_state = random.uniform(420, 520)
last_soil = soil_state

plant_health = 70.0
root_stress = 0.0
surface_water = 0.0

# =========================================================
# 🧠 PID
# =========================================================
Kp = 0.09
Ki = 0.012
Kd = 0.018

pid_integral = 0.0

# =========================================================
# 📡 SENSOR
# =========================================================
sensor_bias = 0.0

def read_sensor(value):
    global sensor_bias
    sensor_bias += random.uniform(-0.02, 0.02)
    sensor_bias *= 0.995
    noise = random.uniform(-2.0, 2.0)
    return value + noise + sensor_bias

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
# 🌿 PHYSICS (HOSE-REALISTIC)
# =========================================================
def simulate():
    global soil_state, plant_health, root_stress, surface_water
    global INJECT_SPIKE, INJECT_AMOUNT

    # 🌬️ evaporation (unchanged but stable)
    evap = (
        (WEATHER["temp"] - 20) * 0.03 +
        WEATHER["sun"] * 0.5 +
        (0.6 - WEATHER["humidity"] / 100) * 0.7
    )
    evap = max(0.15, min(1.5, 0.8 + evap))
    evap *= 0.18

    # 💧 HOSE INPUT (slightly reduced burst)
    if valve_state:
        surface_water += WATER_BUFFER_RATE * 1.2

    # =====================================================
    # 🌊 FIXED WATER DYNAMICS (NO LAG BOMBING)
    # =====================================================

    # continuous per-tick infiltration (no big delayed dump)
    infiltration_rate = 0.18 + (soil_state / SOIL_DRY) * 0.08
    infiltrated = surface_water * infiltration_rate

    surface_water -= infiltrated

    # soil absorption is now DIRECT + controlled
    absorbed = infiltrated * 0.7

    # small residual seepage (prevents abrupt cutoff feel)
    seepage = surface_water * 0.02
    surface_water -= seepage
    absorbed += seepage * 0.5

    # =====================================================

    soil_state -= evap
    soil_state += absorbed

    # 🧪 spike injection (unchanged)
    if INJECT_SPIKE:
        soil_state += INJECT_AMOUNT
        INJECT_AMOUNT *= INJECT_DECAY
        if INJECT_AMOUNT < 1:
            INJECT_SPIKE = False
            INJECT_AMOUNT = 0

    # 🌿 gentle drift
    soil_state -= 0.0006 * (soil_state - 500)

    # overflow handling
    if soil_state > FIELD_CAPACITY:
        soil_state -= (soil_state - FIELD_CAPACITY) * 0.25
        root_stress += 0.05

    soil_state = max(SOIL_WET, min(SOIL_DRY, soil_state))

    # 🌱 plant response
    if soil_state < SAFE_LOW:
        root_stress += 0.05
    elif soil_state > SAFE_HIGH:
        root_stress += 0.04
    else:
        root_stress *= 0.96

    root_stress = max(0, min(10, root_stress))

    if SAFE_LOW <= soil_state <= SAFE_HIGH:
        plant_health += 0.06
    else:
        plant_health -= 0.02

    plant_health -= root_stress * 0.02
    plant_health = max(0, min(100, plant_health))

    return soil_state

# =========================================================
# 🌊 PID CONTROLLER (REAL RESPONSE)
# =========================================================
def apply_valve(soil):
    global valve_state, valve_command_time
    global cycle_state, cycle_start_time, watering_start_soil
    global last_soil, pid_integral

    now = time.time()

    error = TARGET_SOIL - soil
    derivative = soil - last_soil

    pid_integral += error * 0.015
    pid_integral = max(-60, min(60, pid_integral))

    output = (Kp * error) + (Ki * pid_integral) - (Kd * derivative)
    control = max(0.0, min(output, 1.0))

    # cooldown
    if cycle_state == "COOLDOWN":
        if now - cycle_start_time < IRRIGATION_COOLDOWN:
            last_soil = soil
            return
        cycle_state = "IDLE"

    # start watering
    if cycle_state == "IDLE":
        if control > 0.25:
            valve_state = True
            valve_command_time = now
            cycle_state = "WATERING"
            cycle_start_time = now
            watering_start_soil = soil

    # stop watering
    if cycle_state == "WATERING":
        valve_state = True

        if now - valve_command_time < MIN_WATERING_TIME:
            last_soil = soil
            return

        in_band = SAFE_LOW <= soil <= SAFE_HIGH
        weak = control < 0.12

        if in_band or weak:
            valve_state = False
            cycle_state = "COOLDOWN"
            cycle_start_time = now
            watering_start_soil = None
            pid_integral *= 0.6

    last_soil = soil

# =========================================================
# 📡 TELEMETRY
# =========================================================
def send(soil):
    if random.random() < 0.03:
        return

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
                "soil": soil,
                "valve_state": "ON" if valve_state else "OFF",
                "plant_health": plant_health,
                "weather": WEATHER,
                "rssi": random.randint(-70, -40),
            },
            headers=HEADERS,
            timeout=3
        )
    except:
        pass

    print(f"SOIL {soil:.1f} | VALVE {valve_state} | HEALTH {plant_health:.1f}")

# =========================================================
# 🔁 MAIN LOOP
# =========================================================
def run():
    print("🌿 SMART GARDEN SIM STARTED (HOSE + PID + SPIKE SYSTEM)")

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    global soil_state, last_soil

    while True:
        update_weather()

        soil = simulate()
        noisy = read_sensor(soil)

        apply_valve(noisy)
        send(noisy)

        time.sleep(2)
        last_soil = soil

# =========================================================
# 🚀 START
# =========================================================
if __name__ == "__main__":
    run()
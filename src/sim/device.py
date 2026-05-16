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

SAFE_LOW = 400
SAFE_HIGH = 500
TARGET_SOIL = 470

FIELD_CAPACITY = 650

# =========================================================
# 🌊 VALVE SYSTEM
# =========================================================
WATER_BUFFER_RATE = 7

MIN_WATERING_TIME = 12.0
IRRIGATION_COOLDOWN = 30.0

valve_state = False
valve_command_time = 0

cycle_state = "IDLE"
cycle_start_time = 0
watering_start_soil = None

# =========================================================
# 🌦️ WEATHER STATE
# =========================================================
WEATHER = {"temp": 22, "humidity": 50, "sun": 0.5}

def update_weather():
    WEATHER["temp"] += random.uniform(-0.25, 0.25)
    WEATHER["humidity"] += random.uniform(-0.9, 0.9)
    WEATHER["sun"] += random.uniform(-0.06, 0.06)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🌿 STATE
# =========================================================
soil_state = random.uniform(420, 520)
last_soil = soil_state

plant_health = 70.0
root_stress = 0.0
surface_water = 0.0

# =========================================================
# 🧠 PID STATE
# =========================================================
Kp = 0.04
Ki = 0.006
Kd = 0.025

pid_integral = 0.0

# =========================================================
# 📡 SENSOR
# =========================================================
sensor_bias = 0.0

def read_sensor(value):
    global sensor_bias

    sensor_bias += random.uniform(-0.02, 0.02)
    sensor_bias *= 0.995

    noise = random.uniform(-2.5, 2.5)
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
# 🌿 PHYSICS
# =========================================================
def simulate():
    global soil_state, plant_health, root_stress, surface_water

    weather_evap_factor = (
        (WEATHER["temp"] - 20) * 0.04 +
        WEATHER["sun"] * 0.7 +
        (0.6 - WEATHER["humidity"] / 100) * 1.0
    )

    weather_evap_factor = max(0.25, min(2.2, 1.0 + weather_evap_factor))

    evap = weather_evap_factor * 0.21  # balanced evaporation

    if valve_state:
        surface_water += WATER_BUFFER_RATE

    infiltration = surface_water * 0.22
    surface_water -= infiltration

    absorbed = infiltration * 0.86  # tuned for healthy band stability

    soil_state -= evap
    soil_state += absorbed

    soil_state -= 0.002 * (soil_state - 430)  # natural equilibrium pull

    if soil_state > FIELD_CAPACITY:
        runoff = (soil_state - FIELD_CAPACITY) * 0.35
        soil_state -= runoff
        root_stress += 0.05

    soil_state = max(SOIL_WET, min(SOIL_DRY, soil_state))

    if soil_state < SAFE_LOW:
        root_stress += 0.04
    elif soil_state > SAFE_HIGH:
        root_stress += 0.05
    else:
        root_stress *= 0.97

    root_stress = max(0, min(10, root_stress))

    if SAFE_LOW <= soil_state <= SAFE_HIGH:
        plant_health += 0.06
    else:
        plant_health -= 0.02

    plant_health -= root_stress * 0.02
    plant_health = max(0, min(100, plant_health))

    return soil_state

# =========================================================
# 🌊 PID IRRIGATION CONTROLLER
# =========================================================
def apply_valve(soil):
    global valve_state, valve_command_time
    global cycle_state, cycle_start_time, watering_start_soil
    global last_soil, pid_integral

    now = time.time()

    error = TARGET_SOIL - soil
    derivative = soil - last_soil

    pid_integral += error * 0.01
    pid_integral = max(-80, min(80, pid_integral))

    output = (Kp * error) + (Ki * pid_integral) - (Kd * derivative)
    control = max(0.0, min(output, 1.0))

    # =====================================================
    # COOLDOWN
    # =====================================================
    if cycle_state == "COOLDOWN":
        if now - cycle_start_time < IRRIGATION_COOLDOWN:
            last_soil = soil
            return
        cycle_state = "IDLE"

    # =====================================================
    # START WATERING
    # =====================================================
    if cycle_state == "IDLE":
        if control > 0.30:
            valve_state = True
            valve_command_time = now
            cycle_state = "WATERING"
            cycle_start_time = now
            watering_start_soil = soil

    # =====================================================
    # WATERING CONTROL
    # =====================================================
    if cycle_state == "WATERING":
        valve_state = True

        if now - valve_command_time < MIN_WATERING_TIME:
            last_soil = soil
            return

        in_band = SAFE_LOW <= soil <= SAFE_HIGH
        low_control = control < 0.15

        if in_band or low_control:
            valve_state = False
            cycle_state = "COOLDOWN"
            cycle_start_time = now
            watering_start_soil = None
            pid_integral *= 0.5

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
    print("🌿 SMART GARDEN SIM STARTED (PID GREENHOUSE CONTROLLER)")

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
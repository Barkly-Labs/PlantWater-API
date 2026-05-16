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
IDEAL_SOIL = 590

SAFE_LOW = 560
SAFE_HIGH = 615
FIELD_CAPACITY = 650

# =========================================================
# 🌊 VALVE / IRRIGATION
# =========================================================
WATER_BUFFER_RATE = 6
ABSORPTION_RATE = 0.65

WATER_ON = 565
WATER_OFF = 620

MIN_WATERING_TIME = 12.0
IRRIGATION_COOLDOWN = 30.0

# =========================================================
# 🌿 IRRIGATION STATE MACHINE
# =========================================================
cycle_state = "IDLE"   # IDLE | WATERING | COOLDOWN
cycle_start_time = 0
valve_state = False
valve_command_time = 0

watering_start_soil = None

# =========================================================
# 🌿 STATE
# =========================================================
soil_state = random.uniform(580, 620)
last_soil = soil_state

plant_health = 70.0
root_stress = 0.0

surface_water = 0.0

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
# 🌦️ WEATHER
# =========================================================
WEATHER = {"temp": 22, "humidity": 50, "sun": 0.5}

def update_weather():
    WEATHER["temp"] += random.uniform(-0.2, 0.2)
    WEATHER["humidity"] += random.uniform(-0.8, 0.8)
    WEATHER["sun"] += random.uniform(-0.05, 0.05)

    WEATHER["humidity"] = max(20, min(90, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

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

    evap = (
        max(0, WEATHER["temp"] - 18) * 0.25 +
        WEATHER["sun"] * 0.8 +
        (100 - WEATHER["humidity"]) * 0.12
    ) * 0.18

    # 💧 irrigation input
    if valve_state:
        surface_water += WATER_BUFFER_RATE

    infiltration = surface_water * 0.22
    surface_water -= infiltration

    absorbed = infiltration * ABSORPTION_RATE

    soil_state -= evap
    soil_state += absorbed

    soil_state += 0.02 * (IDEAL_SOIL - soil_state)

    if soil_state > FIELD_CAPACITY:
        runoff = (soil_state - FIELD_CAPACITY) * 0.35
        soil_state -= runoff
        root_stress += 0.05

    soil_state = max(SOIL_WET, min(SOIL_DRY, soil_state))

    # 🌱 stress model
    if soil_state < 540:
        root_stress += 0.04
    elif soil_state > 620:
        root_stress += 0.05
    else:
        root_stress *= 0.97

    root_stress = max(0, min(10, root_stress))

    # 🌿 health model
    if SAFE_LOW <= soil_state <= SAFE_HIGH:
        plant_health += 0.05
    elif 520 <= soil_state < SAFE_LOW or SAFE_HIGH < soil_state <= 650:
        plant_health -= 0.01
    else:
        plant_health -= 0.03

    plant_health -= root_stress * 0.02
    plant_health = max(0, min(100, plant_health))

    return soil_state

# =========================================================
# 🌊 IRRIGATION CONTROLLER (CYCLE-BASED)
# =========================================================
def apply_valve(soil):
    global valve_state, valve_command_time
    global cycle_state, cycle_start_time, watering_start_soil
    global last_soil

    now = time.time()
    soil_velocity = soil - last_soil

    # =====================================================
    # 🌿 COOLDOWN PHASE (no decisions allowed)
    # =====================================================
    if cycle_state == "COOLDOWN":
        if now - cycle_start_time < IRRIGATION_COOLDOWN:
            last_soil = soil
            return
        else:
            cycle_state = "IDLE"

    # =====================================================
    # 🌱 START IRRIGATION CYCLE
    # =====================================================
    if cycle_state == "IDLE":
        if soil < WATER_ON or (soil < 580 and soil_velocity < -0.5):

            valve_state = True
            valve_command_time = now
            cycle_start_time = now
            watering_start_soil = soil

            cycle_state = "WATERING"
            last_soil = soil
            return

    # =====================================================
    # 💧 WATERING PHASE
    # =====================================================
    if cycle_state == "WATERING":
        valve_state = True

        # ⛔ minimum watering time
        if now - valve_command_time < MIN_WATERING_TIME:
            last_soil = soil
            return

        # 🌱 stop based on delivered water amount
        if watering_start_soil is not None:
            if soil - watering_start_soil > 12:
                valve_state = False
                cycle_state = "COOLDOWN"
                cycle_start_time = now
                watering_start_soil = None
                last_soil = soil
                return

        # 💧 safety shutoff
        if soil > WATER_OFF:
            valve_state = False
            cycle_state = "COOLDOWN"
            cycle_start_time = now
            watering_start_soil = None

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
                "valve_state": "ON" if valve_state else "OFF",
                "plant_health": plant_health,
                "rssi": random.randint(-70, -40),
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
    print("🌿 SMART GARDEN SIM STARTED (CYCLE-BASED CONTROLLER)")

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
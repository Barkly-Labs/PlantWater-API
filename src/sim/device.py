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
TICK_RATE = 2.0

# =========================================================
# 🪵 LOG FILE (RESET EACH RUN)
# =========================================================
LOG_FILE = "device.log"

if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# =========================================================
# 🧪 TEST MODE (HARDWARE QA SWITCH)
# =========================================================
TEST_MODE = True  # 🔴 turn True for chaos testing

# =========================================================
# 🌦️ WEATHER
# =========================================================
WEATHER = {"temp": 22, "humidity": 50, "sun": 0.5}

def update_weather():
    try:
        r = requests.get(f"{SERVER}/api/weather", headers=HEADERS, timeout=2)
        if r.status_code == 200:
            d = r.json()
            WEATHER["temp"] = WEATHER["temp"] * 0.7 + d["temp"] * 0.3
            WEATHER["humidity"] = WEATHER["humidity"] * 0.7 + d["humidity"] * 0.3
            WEATHER["sun"] = WEATHER["sun"] * 0.7 + d["sun"] * 0.3
    except:
        pass

    WEATHER["temp"] += random.uniform(-0.15, 0.15)
    WEATHER["humidity"] = max(15, min(95, WEATHER["humidity"] + random.uniform(-0.4, 0.4)))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"] + random.uniform(-0.02, 0.02)))

# =========================================================
# 🌱 SOIL MODEL (LAYERS)
# =========================================================
surface = 460.0
root = 480.0
deep = 510.0

FIELD_CAPACITY = 650
WILTING = 300

# =========================================================
# 💧 VALVE SYSTEM
# =========================================================
valve = False
valve_pressure = 0.0

# =========================================================
# 🌿 PLANT MODEL
# =========================================================
plant_health = 70.0
stress = 0.0

# =========================================================
# 🧪 RANDOM STRESS SYSTEM (TEST MODE ONLY)
# =========================================================
def maybe_shock():
    global surface, root, deep

    if not TEST_MODE:
        return

    if random.random() < 0.04:

        event = random.choice([
            "heat_spike",
            "rain_burst",
            "dry_wind",
            "sensor_noise",
            "absorption_fault"
        ])

        if event == "heat_spike":
            surface -= random.uniform(8, 22)

        elif event == "rain_burst":
            surface += random.uniform(10, 28)

        elif event == "dry_wind":
            surface -= random.uniform(6, 18)

        elif event == "sensor_noise":
            surface += random.uniform(-8, 8)

        elif event == "absorption_fault":
            root *= 1.02  # bad soil behavior

# =========================================================
# 🌊 PHYSICS ENGINE
# =========================================================
def simulate():

    global surface, root, deep
    global plant_health, stress
    global valve_pressure

    # -----------------------------
    # 🌬️ evaporation
    # -----------------------------
    evap = (
        (WEATHER["temp"] - 20) * 0.05 +
        WEATHER["sun"] * 0.7 +
        (0.6 - WEATHER["humidity"] / 100) * 0.9
    ) * 0.22


    surface -= max(0.05, evap)

    # -----------------------------
    # 💧 natural flow
    # -----------------------------
    flow_sr = (surface - root) * 0.10
    surface -= flow_sr
    root += flow_sr

    flow_rd = (root - deep) * 0.03
    root -= flow_rd
    deep += flow_rd

    # -----------------------------
    # 🚿 valve pressure (realistic lag)
    # -----------------------------
    if valve:
        valve_pressure += 6.0

    release = valve_pressure * 0.25
    surface += release
    valve_pressure -= release
    valve_pressure *= 0.96

    # -----------------------------
    # 🧪 TEST SHOCKS
    # -----------------------------
    maybe_shock()

    # -----------------------------
    # 🌱 plant response
    # -----------------------------
    avg = (surface + root) / 2

    if avg < WILTING:
        stress += 0.09
    elif avg > FIELD_CAPACITY:
        stress += 0.05
    else:
        stress *= 0.97

    stress = max(0, min(10, stress))

    plant_health += 0.025 if 420 <= avg <= 560 else -0.03
    plant_health -= stress * 0.02
    plant_health = max(0, min(100, plant_health))

    return avg

# =========================================================
# 🎛️ CONTROLLER (ESP32 STYLE)
# =========================================================
def controller(moisture):

    global valve

    # simple hardware logic (intentional, not fancy PID)
    if moisture > 600:
        valve = True
    elif moisture < 500:
        valve = False

# =========================================================
# 📡 TELEMETRY
# =========================================================
def send(moisture):

    sensors = [moisture + random.uniform(-2.5, 2.5) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json={
                "bed_id": BED_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "soil": avg,
                "sensors": sensors,
                "valve": valve,
                "plant_health": plant_health,
                "weather": WEATHER,
                "test_mode": TEST_MODE
            },
            headers=HEADERS,
            timeout=2
        )
    except:
        pass

    log(f"SOIL {avg:.1f} | VALVE {valve} | HEALTH {plant_health:.1f}")

# =========================================================
# 💓 HEARTBEAT
# =========================================================
def heartbeat():
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
# 🔁 MAIN LOOP
# =========================================================
def run():

    threading.Thread(target=heartbeat, daemon=True).start()

    print("🌿 GARDEN SIM STARTED (TEST MODE =", TEST_MODE, ")")

    while True:

        update_weather()

        moisture = simulate()
        controller(moisture)
        send(moisture)

        time.sleep(TICK_RATE)

if __name__ == "__main__":
    run()
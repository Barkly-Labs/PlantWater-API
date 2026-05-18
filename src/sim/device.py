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
LOG_FILE = "device.log"

TICK_RATE = 2.0

EVENT_MODE = True

# =========================================================
# 🌦️ WEATHER (smoothed + chaotic drift)
# =========================================================
WEATHER = {"temp": 22, "humidity": 50, "sun": 0.5}

# 🧹 reset log file each run (fresh boot like hardware restart)
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

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

    # natural drift
    WEATHER["temp"] += random.uniform(-0.15, 0.15)
    WEATHER["humidity"] += random.uniform(-0.4, 0.4)
    WEATHER["sun"] += random.uniform(-0.02, 0.02)

    WEATHER["humidity"] = max(15, min(95, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🌱 SOIL LAYERS (REALISTIC HYDROLOGY)
# =========================================================
surface = 460.0
root = 480.0
deep = 510.0

FIELD_CAPACITY = 650
WILTING = 300

# =========================================================
# 💧 VALVE PHYSICS (REAL HARDWARE BEHAVIOR)
# =========================================================
valve = False
valve_pressure = 0.0
valve_cooldown = 0

# =========================================================
# 🌿 PLANT MODEL (STRESS MEMORY)
# =========================================================
plant_health = 70.0
stress = 0.0

# =========================================================
# 🧪 RANDOM ENVIRONMENT SHOCKS (THIS IS YOUR REQUEST)
# =========================================================
shock_timer = random.randint(20, 50)

def maybe_shock():
    global surface

    if not EVENT_MODE:
        return

    # rare but realistic system events
    if random.random() < 0.015:

        event = random.choice([
            "heatwave",
            "rainburst",
            "sensor_noise_spike",
            "dry_wind"
        ])

        if event == "heatwave":
            surface -= random.uniform(15, 30)

        elif event == "rainburst":
            surface += random.uniform(20, 40)

        elif event == "dry_wind":
            surface -= random.uniform(10, 22)

        elif event == "sensor_noise_spike":
            # simulate hardware glitch, not soil change
            pass
# =========================================================
# 🌊 PHYSICS CORE (REALISTIC WATER SYSTEM)
# =========================================================
def simulate():

    global surface, root, deep
    global plant_health, stress
    global valve_pressure, valve_cooldown

    # -----------------------------
    # 🌬️ EVAP (surface heavy)
    # -----------------------------
    evap = (
        (WEATHER["temp"] - 20) * 0.05 +
        WEATHER["sun"] * 0.7 +
        (0.6 - WEATHER["humidity"] / 100) * 0.9
    ) * 0.22

    surface -= max(0.05, evap)

    # -----------------------------
    # 💧 NATURAL INFILTRATION
    # -----------------------------
    flow_sr = (surface - root) * 0.10
    surface -= flow_sr
    root += flow_sr

    flow_rd = (root - deep) * 0.03
    root -= flow_rd
    deep += flow_rd

    # -----------------------------
    # 🚿 VALVE PRESSURE SYSTEM
    # -----------------------------
    if valve:
        valve_pressure += 6.0

    # delayed release (IMPORTANT REALISM)
    release = valve_pressure * 0.25
    surface += release
    valve_pressure -= release

    # valve bleed even when OFF
    valve_pressure *= 0.96

    # -----------------------------
    # 🧪 SHOCK SYSTEM
    # -----------------------------
    maybe_shock()

    # -----------------------------
    # 🌱 PLANT RESPONSE (slow + memory)
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
# 🎛️ CONTROLLER (ESP32 STYLE SIMPLE RULES)
# =========================================================
def controller(moisture):

    global valve, valve_cooldown

    valve_cooldown = max(0, valve_cooldown - 1)

    # HARD SAFETY DRY RULE
    if moisture > 600 and valve_cooldown == 0:
        valve = True

    # STOP RULE
    if moisture < 500:
        valve = False
        valve_cooldown = 6

# =========================================================
# 🪵 LOGGING (IMPORTANT: LIKE DEVICE)
# =========================================================
def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# =========================================================
# 📡 TELEMETRY
# =========================================================
def send(moisture):

    sensors = [moisture + random.uniform(-2.5, 2.5) for _ in range(5)]
    avg = sum(sensors) / len(sensors)
    valve_state = "ON" if valve else "OFF"
    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json={
                "bed_id": BED_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "average": avg,
                "sensors": sensors,
                "valve_state": valve_state,
                "plant_health": plant_health,
                "weather": WEATHER,
                "rssi": int(random.uniform(-70, -40)),
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

    print("🌿 HARDWARE-LEVEL GARDEN SIM RUNNING")

    while True:

        update_weather()

        m = simulate()
        controller(m)
        send(m)

        time.sleep(TICK_RATE)

if __name__ == "__main__":
    run()
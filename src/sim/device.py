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
# 🌦️ WEATHER
# =========================================================
WEATHER = {"temp": 22, "humidity": 50, "sun": 0.5}

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

    WEATHER["temp"] += random.uniform(-0.15, 0.15)
    WEATHER["humidity"] += random.uniform(-0.4, 0.4)
    WEATHER["sun"] += random.uniform(-0.02, 0.02)

    WEATHER["humidity"] = max(15, min(95, WEATHER["humidity"]))
    WEATHER["sun"] = max(0, min(1, WEATHER["sun"]))

# =========================================================
# 🌱 SOIL LAYERS
# =========================================================
surface = 460.0
root = 480.0
deep = 510.0

FIELD_CAPACITY = 650
WILTING = 300

# =========================================================
# 💧 VALVE
# =========================================================
valve = False
valve_pressure = 0.0
valve_cooldown = 0

# =========================================================
# 🌿 PLANT MODEL
# =========================================================
plant_health = 70.0
stress = 0.0
event_noise = 0.0

# =========================================================
# 🧪 EVENT MEMORY SYSTEM (NEW CORE UPGRADE)
# =========================================================
event_surface_factor = 1.0
event_root_factor = 1.0

# slowly returns to normal
def decay_events():
    global event_surface_factor, event_root_factor

    event_surface_factor = min(1.0, event_surface_factor + 0.002)
    event_root_factor = min(1.0, event_root_factor + 0.0015)

# =========================================================
# 🌪 EVENTS
# =========================================================
def maybe_shock():
    global surface, root, deep
    global stress
    global event_noise
    

    if not EVENT_MODE:
        return

    # decay leftover chaos over time
    event_noise *= 0.92

    if random.random() < 0.02:

        event = random.choice([
            "heatwave",
            "dry_spike",
            "rainburst",
            "sensor_glitch"
        ])

        # =====================================================
        # 🔥 HEATWAVE (slow system-wide drying + lingering stress)
        # =====================================================
        if event == "heatwave":
            log("🔥 HEATWAVE EVENT TRIGGERED")
            stress += 0.8

            surface *= 0.94
            root *= 0.97
            deep *= 0.99

            # lingering drying effect
            event_noise += 0.6

        # =====================================================
        # 🌬️ DRY SPIKE (sharp loss + evaporation multiplier)
        # =====================================================
        elif event == "dry_spike":
            log("🌬️ DRY SPIKE EVENT TRIGGERED")
            stress += 1.0

            surface -= random.uniform(10, 22)
            root *= 0.98
            deep *= 0.985

            # makes next few ticks harsher
            event_noise += 0.9

        # =====================================================
        # 🌧️ RAIN BURST (overload + instability)
        # =====================================================
        elif event == "rainburst":
            log("🌧️ RAIN BURST EVENT TRIGGERED")

            surface += random.uniform(20, 40)

            # delay redistribution (important realism)
            root += surface * 0.08
            deep += root * 0.03

            stress -= 0.3  # temporary relief
            event_noise += 0.7

        # =====================================================
        # 📡 SENSOR GLITCH (NOISE ONLY, BUT STRONG)
        # =====================================================
        elif event == "sensor_glitch":
            log("📡 SENSOR GLITCH EVENT TRIGGERED")

            stress += 0.3

            # THIS is what you were missing:
            # actual perception chaos
            event_noise += 2.5
# =========================================================
# 🌊 SIMULATION CORE
# =========================================================
def simulate():
    global surface, root, deep, plant_health, stress
    global valve_pressure, valve_cooldown
    global event_surface_factor, event_root_factor

    evap = (
        (WEATHER["temp"] - 20) * 0.05 +
        WEATHER["sun"] * 0.7 +
        (0.6 - WEATHER["humidity"] / 100) * 0.9
    ) * 0.22

    surface -= max(0.05, evap)

    flow_sr = (surface - root) * 0.10
    surface -= flow_sr
    root += flow_sr

    flow_rd = (root - deep) * 0.03
    root -= flow_rd
    deep += flow_rd

    # =====================================================
    # 🌪 APPLY EVENT MEMORY (THIS IS THE FIX)
    # =====================================================
    surface *= event_surface_factor
    root *= event_root_factor

    decay_events()

    # =====================================================
    # 🚿 VALVE
    # =====================================================
    if valve:
        valve_pressure += 6.0

    release = valve_pressure * 0.25
    surface += release
    valve_pressure -= release
    valve_pressure *= 0.96

    maybe_shock()

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
# 🎛 CONTROLLER
# =========================================================
def controller(moisture):
    global valve, valve_cooldown

    valve_cooldown = max(0, valve_cooldown - 1)

    if moisture > 600 and valve_cooldown == 0:
        valve = True

    if moisture < 500:
        valve = False
        valve_cooldown = 6

# =========================================================
# 🪵 LOGGING
# =========================================================
def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# =========================================================
# 📡 SEND
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
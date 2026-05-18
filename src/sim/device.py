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
# 🌦️ WEATHER SYSTEM
# =========================================================
class Weather:
    def __init__(self):
        self.temp = 22
        self.humidity = 50
        self.sun = 0.5

    def update(self):
        try:
            r = requests.get(f"{SERVER}/api/weather", headers=HEADERS, timeout=2)
            if r.status_code == 200:
                d = r.json()
                self.temp = self.temp * 0.75 + d["temp"] * 0.25
                self.humidity = self.humidity * 0.75 + d["humidity"] * 0.25
                self.sun = self.sun * 0.75 + d["sun"] * 0.25
        except:
            pass

        self.temp += random.uniform(-0.1, 0.1)
        self.humidity += random.uniform(-0.3, 0.3)
        self.sun += random.uniform(-0.02, 0.02)

        self.humidity = max(15, min(95, self.humidity))
        self.sun = max(0, min(1, self.sun))


# =========================================================
# 🌱 SOIL MODEL (FIXED: NO MORE BOUNCY REBOUNDS)
# =========================================================
class Soil:
    def __init__(self):
        self.surface = 460.0
        self.root = 480.0
        self.deep = 510.0

        self.FIELD_CAPACITY = 650
        self.WILTING = 300

        # system memory (prevents instant correction bounce)
        self.disturbance = 0.0

    def evaporate(self, weather):
        evap = (
            (weather.temp - 20) * 0.04 +
            weather.sun * 0.6 +
            (0.6 - weather.humidity / 100) * 0.8
        ) * 0.20

        self.surface -= max(0.02, evap)

    def flow(self):
        sr = (self.surface - self.root) * 0.08
        self.surface -= sr
        self.root += sr

        rd = (self.root - self.deep) * 0.02
        self.root -= rd
        self.deep += rd

    def equilibrium(self):
        base = 460

        # decay old disturbances slowly (no instant reset)
        self.disturbance *= 0.96

        # soft pull toward equilibrium
        self.surface += (base - self.surface) * 0.015 + self.disturbance * 0.02
        self.root += (base - self.root) * 0.010 + self.disturbance * 0.01
        self.deep += (base - self.deep) * 0.006 + self.disturbance * 0.005

    def clamp(self):
        self.surface = max(0, min(self.surface, 900))
        self.root = max(0, min(self.root, 850))
        self.deep = max(0, min(self.deep, 800))

    def avg(self):
        return (self.surface + self.root) / 2


# =========================================================
# 💧 VALVE SYSTEM (SMOOTHER CONTROL, LESS OSCILLATION)
# =========================================================
class Valve:
    def __init__(self):
        self.on = False
        self.pressure = 0.0
        self.cooldown = 0

    def update(self, soil):
        self.cooldown = max(0, self.cooldown - 1)

        avg = soil.avg()

        if avg > 610:
            self.on = True
        elif avg < 520 and self.cooldown == 0:
            self.on = False
            self.cooldown = 8

        if self.on:
            self.pressure += 4.0
        else:
            self.pressure *= 0.97

        release = self.pressure * 0.18
        soil.surface += release
        self.pressure -= release


# =========================================================
# 🌿 PLANT MODEL
# =========================================================
class Plant:
    def __init__(self):
        self.health = 70.0
        self.stress = 0.0

    def update(self, soil):
        avg = soil.avg()

        if avg < soil.WILTING:
            self.stress += 0.08
        elif avg > soil.FIELD_CAPACITY:
            self.stress += 0.04
        else:
            self.stress *= 0.97

        self.stress = max(0, min(10, self.stress))

        if 420 <= avg <= 560:
            self.health += 0.02
        else:
            self.health -= 0.025

        self.health -= self.stress * 0.015
        self.health = max(0, min(100, self.health))


# =========================================================
# 🌪 EVENT SYSTEM (FIXED: NO HARD REBOUNDS)
# =========================================================
class Events:
    def __init__(self):
        self.noise = 0.0

    def trigger(self, soil, plant, valve):
        if not EVENT_MODE:
            return

        self.noise *= 0.9

        if random.random() < 0.02:
            event = random.choice([
                "heatwave",
                "dry_spike",
                "rainburst",
                "sensor_glitch"
            ])

            log(f"🌪 EVENT: {event}")

            if event == "heatwave":
                log("🔥 HEATWAVE TRIGGERED")
                plant.stress += 0.6
                valve.on = True
                soil.disturbance += 35
                soil.surface += random.uniform(30, 90)
                self.noise += 2.0

            elif event == "dry_spike":
                log("🌬 DRY SPIKE")
                plant.stress += 0.8
                valve.on = True
                soil.disturbance -= 40
                soil.surface -= random.uniform(50, 120)
                self.noise += 2.5

            elif event == "rainburst":
                log("🌧 RAIN BURST TRIGGERED")
                soil.disturbance += 50
                soil.surface += random.uniform(120, 180)
                soil.root += random.uniform(40, 80)
                plant.stress -= 0.4
                self.noise += 2.8

            elif event == "sensor_glitch":
                plant.stress += 0.2
                self.noise += 1.5

            soil.clamp()

    def apply_noise(self, soil):
        noise = self.noise * random.uniform(0.8, 1.2)

        soil.surface += noise * 0.5
        soil.root += noise * 0.3
        soil.deep += noise * 0.2

        self.noise *= 0.85


# =========================================================
# 🪵 LOGGING
# =========================================================
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# =========================================================
# 📡 SEND
# =========================================================
def send(soil, plant, valve, weather):
    avg = soil.avg()

    sensors = [avg + random.uniform(-2.5, 2.5) for _ in range(5)]

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json={
                "bed_id": BED_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "average": avg,
                "sensors": sensors,
                "valve_state": "ON" if valve.on else "OFF",
                "plant_health": plant.health,
                "weather": {
                    "temp": weather.temp,
                    "humidity": weather.humidity,
                    "sun": weather.sun
                },
                "rssi": int(random.uniform(-70, -40)),
            },
            headers=HEADERS,
            timeout=2
        )
    except:
        pass

    log(f"SOIL {avg:.1f} | VALVE {valve.on} | HEALTH {plant.health:.1f}")


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
    weather = Weather()
    soil = Soil()
    valve = Valve()
    plant = Plant()
    events = Events()

    threading.Thread(target=heartbeat, daemon=True).start()

    print("🌿 FIXED GARDEN SIM RUNNING")

    while True:
        weather.update()

        soil.evaporate(weather)
        soil.flow()

        events.trigger(soil, plant, valve)
        events.apply_noise(soil)

        valve.update(soil)
        soil.equilibrium()
        soil.clamp()

        plant.update(soil)

        send(soil, plant, valve, weather)

        time.sleep(TICK_RATE)


if __name__ == "__main__":
    run()
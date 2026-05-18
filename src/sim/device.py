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
                self.temp = self.temp * 0.7 + d["temp"] * 0.3
                self.humidity = self.humidity * 0.7 + d["humidity"] * 0.3
                self.sun = self.sun * 0.7 + d["sun"] * 0.3
        except:
            pass

        # natural drift
        self.temp += random.uniform(-0.15, 0.15)
        self.humidity += random.uniform(-0.4, 0.4)
        self.sun += random.uniform(-0.02, 0.02)

        self.humidity = max(15, min(95, self.humidity))
        self.sun = max(0, min(1, self.sun))


# =========================================================
# 🌱 SOIL MODEL
# =========================================================
class Soil:
    def __init__(self):
        self.surface = 460.0
        self.root = 480.0
        self.deep = 510.0

        self.FIELD_CAPACITY = 650
        self.WILTING = 300

    def evaporate(self, weather):
        evap = (
            (weather.temp - 20) * 0.05 +
            weather.sun * 0.7 +
            (0.6 - weather.humidity / 100) * 0.9
        ) * 0.22

        self.surface -= max(0.05, evap)

    def flow(self):
        flow_sr = (self.surface - self.root) * 0.10
        self.surface -= flow_sr
        self.root += flow_sr

        flow_rd = (self.root - self.deep) * 0.03
        self.root -= flow_rd
        self.deep += flow_rd

    def clamp(self):
        self.surface = max(0, min(self.surface, 900))
        self.root = max(0, min(self.root, 850))
        self.deep = max(0, min(self.deep, 800))

    def avg(self):
        return (self.surface + self.root) / 2


# =========================================================
# 💧 VALVE SYSTEM
# =========================================================
class Valve:
    def __init__(self):
        self.on = False
        self.pressure = 0.0
        self.cooldown = 0

    def update(self, soil):
        self.cooldown = max(0, self.cooldown - 1)

        if soil.avg() > 600 and self.cooldown == 0:
            self.on = True

        if soil.avg() < 500:
            self.on = False
            self.cooldown = 6

        if self.on:
            self.pressure += 6.0

        release = self.pressure * 0.25
        soil.surface += release

        self.pressure -= release
        self.pressure *= 0.96


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
            self.stress += 0.09
        elif avg > soil.FIELD_CAPACITY:
            self.stress += 0.05
        else:
            self.stress *= 0.97

        self.stress = max(0, min(10, self.stress))

        if 420 <= avg <= 560:
            self.health += 0.025
        else:
            self.health -= 0.03

        self.health -= self.stress * 0.02
        self.health = max(0, min(100, self.health))


# =========================================================
# 🌪 EVENT SYSTEM
# =========================================================
class Events:
    def __init__(self):
        self.noise = 0.0

    def trigger(self, soil, plant, valve):
        if not EVENT_MODE:
            return

        self.noise *= 0.92

        if random.random() < 0.02:
            event = random.choice([
                "heatwave",
                "dry_spike",
                "rainburst",
                "sensor_glitch"
            ])

            log(f"🌪 EVENT: {event}")

            if event == "heatwave":
                log("🔥 HEATWAVE EVENT TRIGGERED")

                plant.stress += 0.8
                valve.on = True

                # 🌡️ FORCE SOIL SPIKE INTO HIGH MOISTURE STATE
                spike = random.uniform(600, 800)

                soil.surface = max(soil.surface, spike)
                soil.surface += random.uniform(40, 120)

                soil.root += random.uniform(20, 60)
                soil.deep += random.uniform(10, 40)

                soil.clamp()

                self.noise += 2.0

            elif event == "dry_spike":
                log("🌬️ DRY SPIKE EVENT TRIGGERED")

                plant.stress += 1.0
                valve.on = True

                soil.surface = random.uniform(250, 420)
                soil.root *= 0.85
                soil.deep *= 0.9

                soil.clamp()

                self.noise += 3.0

            elif event == "rainburst":
                soil.surface -= random.uniform(120, 250)
                plant.stress -= 0.6

            elif event == "sensor_glitch":
                plant.stress += 0.3

            self.noise += random.uniform(1.0, 3.5)

    def apply_noise(self, soil):
        noise = self.noise * random.uniform(0.8, 1.2)

        soil.surface += noise * 0.6
        soil.root += noise * 0.3
        soil.deep += noise * 0.1

        self.noise *= 0.88


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
# 📡 NETWORK
# =========================================================
def send(soil, plant, valve, weather):
    moisture = soil.avg()

    sensors = [moisture + random.uniform(-2.5, 2.5) for _ in range(5)]
    avg = sum(sensors) / len(sensors)

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

    print("🌿 CLEAN GARDEN SIM RUNNING")

    while True:
        weather.update()

        soil.evaporate(weather)
        soil.flow()

        events.trigger(soil, plant, valve)
        events.apply_noise(soil)

        valve.update(soil)
        soil.clamp()

        plant.update(soil)

        send(soil, plant, valve, weather)

        time.sleep(TICK_RATE)


if __name__ == "__main__":
    run()
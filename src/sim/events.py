import random
from config import EVENT_MODE
from utils import log


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
                
            soil.clamp()

    def apply_noise(self, soil):
        noise = self.noise * random.uniform(0.8, 1.2)

        soil.surface += noise * 0.5
        soil.root += noise * 0.3
        soil.deep += noise * 0.2

        self.noise *= 0.85

import random
from config import EVENT_MODE
from utils import log


# =========================================================
# 🌪 EVENT SYSTEM (CLEAN + CONSISTENT PHYSICS)
# =========================================================
class Events:
    def __init__(self):
        self.noise = 0.0

    def trigger(self, soil, plant, valve):
        if not EVENT_MODE:
            return

        # decay noise slowly
        self.noise *= 0.9

        # small chance of event
        if random.random() < 0.02:

            event = random.choice([
                "heatwave",
                "dry_spike",
                "rainburst",
            ])

            log(f"🌪 EVENT: {event}")

            # =================================================
            # 🔥 HEATWAVE (dries soil)
            # =================================================
            if event == "heatwave":
                log("🔥 HEATWAVE TRIGGERED")

                plant.stress += 0.6
                valve.on = True

                soil.disturbance += 40
                soil.surface += random.uniform(40, 90)
                soil.root += random.uniform(20, 50)

                self.noise += 2.0

            # =================================================
            # 🌬 DRY SPIKE (strong drying event)
            # =================================================
            elif event == "dry_spike":
                log("🌬 DRY SPIKE")

                plant.stress += 0.8
                valve.on = True

                soil.disturbance += 70
                soil.surface += random.uniform(80, 140)
                soil.root += random.uniform(40, 90)
                soil.deep += random.uniform(10, 30)

                self.noise += 2.5

            # =================================================
            # 🌧 RAIN BURST (WETTING EVENT - FIXED)
            # =================================================
            elif event == "rainburst":
                log("🌧 RAIN BURST TRIGGERED")

                plant.stress -= 0.4

                # IMPORTANT: wet = LOWER soil values
                soil.disturbance -= 80

                soil.surface -= random.uniform(120, 200)
                soil.root -= random.uniform(60, 120)
                soil.deep -= random.uniform(20, 60)

                self.noise += 3.0

            soil.clamp()

    # =========================================================
    # 🌫 NOISE SYSTEM (symmetrical + damped)
    # =========================================================
    def apply_noise(self, soil):

        noise = self.noise * random.uniform(-1.0, 1.0)

        soil.surface += noise * 0.5
        soil.root += noise * 0.3
        soil.deep += noise * 0.2

        self.noise *= 0.85
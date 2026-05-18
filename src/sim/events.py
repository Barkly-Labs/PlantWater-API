import random
from config import EVENT_MODE
from utils import log


class Events:
    def __init__(self):
        self.noise = 0.0

        # 🎛 CONTROL KNOBS
        self.event_rate = 0.02
        self.event_scale = 1.0

        # optional debugging control
        self.force_next_event = None

        # 🌡 FIX: required state for heatwave system
        self.heatwave_force = 0.0


    def trigger(self, soil, plant, valve):
        self.noise *= 0.9

        event = None

        # 🎮 MANUAL OVERRIDE
        if self.force_next_event:
            event = self.force_next_event
            self.force_next_event = None

        elif EVENT_MODE:
            if random.random() > self.event_rate:
                return

            event = random.choice([
                "heatwave",
                "dry_spike",
                "rainburst",
            ])

        else:
            return

        log(f"🌪 EVENT: {event}")

        # =========================
        # 🔥 HEATWAVE
        # =========================
        if event == "heatwave":
            log("🔥 HEATWAVE TRIGGERED")

            plant.stress += 0.6 * self.event_scale
            valve.on = True

            spike = random.uniform(120, 180) * self.event_scale

            soil.surface += spike
            soil.disturbance += 40 * self.event_scale

            self.heatwave_force += spike * 0.8
            self.noise += 1.5 * self.event_scale


        # =========================
        # 🌬 DRY SPIKE
        # =========================
        elif event == "dry_spike":
            log("🌬 DRY SPIKE")

            plant.stress += 0.5 * self.event_scale
            valve.on = True

            soil.disturbance -= 10 * self.event_scale
            soil.surface += random.uniform(20, 45) * self.event_scale

            self.noise += 1.5 * self.event_scale


        # =========================
        # 🌧 RAIN BURST
        # =========================
        elif event == "rainburst":
            log("🌧 RAIN BURST TRIGGERED")

            soil.disturbance += 25 * self.event_scale
            soil.surface += random.uniform(40, 80) * self.event_scale
            soil.root += random.uniform(15, 30) * self.event_scale

            plant.stress -= 0.3 * self.event_scale

            self.noise += 1.8 * self.event_scale


        soil.clamp()


    def apply_noise(self, soil):
        noise = self.noise * random.uniform(0.8, 1.2)

        # 🌡 heatwave decay (NOW SAFE + REALISTIC)
        if self.heatwave_force > 0:
            bleed = self.heatwave_force * 0.06

            soil.surface -= bleed
            self.heatwave_force *= 0.92

        soil.surface += noise * 0.4
        soil.root += noise * 0.25
        soil.deep += noise * 0.15

        self.noise *= 0.85


    # =====================================================
    # 🧪 DEBUG TOOLING
    # =====================================================
    def set_event_rate(self, rate):
        self.event_rate = max(0.0, min(1.0, rate))

    def set_event_scale(self, scale):
        self.event_scale = max(0.1, scale)

    def test_event(self, name):
        self.force_next_event = name
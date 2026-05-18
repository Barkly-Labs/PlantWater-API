import random
from config import EVENT_MODE
from utils import log


class Events:
    def __init__(self):
        self.noise = 0.0

        # 🎛 CONTROL KNOBS
        self.event_rate = 0.02
        self.event_scale = 1.0

        # 🎮 manual trigger system
        self.force_next_event = None

        # 🌡 heatwave persistence system
        self.heatwave_force = 0.0

        # 💧 wet system (MISSING BEFORE — THIS WAS BREAKING SYMMETRY)
        self.wet_force = 0.0
        self.wet_target = 0.0
        self.wet_hold = 0

        # 🌡 PEAK SYSTEM
        self.peak_value = 0.0
        self.peak_hold = 0

        # 🧠 heatwave interaction lock
        self.heatwave_lock = 0


    def trigger(self, soil, plant, valve):
        self.noise *= 0.9

        event = None

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

        # =====================================================
        # 🔥 HEATWAVE
        # =====================================================
        if event == "heatwave":
            log("🔥 HEATWAVE TRIGGERED")

            plant.stress += 1.2 * self.event_scale
            valve.on = True

            spike = random.uniform(300, 420) * self.event_scale

            soil.surface += spike
            soil.disturbance += 90 * self.event_scale

            self.peak_value = soil.surface
            self.peak_hold = 6

            self.heatwave_lock = 3

            self.heatwave_force += spike * 2.4
            self.noise += 2.2 * self.event_scale


        # =====================================================
        # 🌬 DRY SPIKE
        # =====================================================
        elif event == "dry_spike":
            log("🌬 DRY SPIKE")

            plant.stress += 0.4 * self.event_scale
            valve.on = True

            spike = random.uniform(18, 35) * self.event_scale
            soil.surface += spike

            soil.disturbance += 12 * self.event_scale

            self.heatwave_force += spike * 0.4
            self.noise += 1.0 * self.event_scale


        # =====================================================
        # 🌧 RAIN BURST (HARD SATURATION SYSTEM)
        # =====================================================
        elif event == "rainburst":
            log("🌧 RAIN BURST TRIGGERED")

            plant.stress -= 0.3 * self.event_scale

            self.wet_target = random.uniform(180, 220)
            self.wet_hold = 10

            self.wet_force += random.uniform(140, 220) * self.event_scale

            soil.root += random.uniform(30, 60) * self.event_scale
            soil.disturbance += 20 * self.event_scale

            self.noise += 1.8 * self.event_scale

        soil.clamp()


    def apply_noise(self, soil):

        # =====================================================
        # 🌧 WET SYSTEM (must run FIRST so it dominates state)
        # =====================================================
        # 🌧 WET SYSTEM (strong equilibrium instead of weak target flicker)
        if self.wet_force > 0:
            self.wet_force *= 0.94

            pressure = self.wet_force * 0.03

            # pull DOWN more aggressively
            soil.surface -= pressure

            # small chaotic spread
            soil.surface += random.uniform(-pressure * 0.2, pressure * 0.05)

        # 🌧 HARD SATURATION LOCK (this is what you’re missing)
        if self.wet_hold > 0:
            # stronger anchoring toward 200 range
            soil.surface = (soil.surface * 0.4) + (self.wet_target * 0.6)

            self.wet_hold -= 1
        else:
            # slow evaporation bias (important)
            soil.surface += 0.15


        # =====================================================
        # 🌡 PEAK SYSTEM
        # =====================================================
        if self.peak_hold > 0:
            soil.surface = max(soil.surface, self.peak_value)
            self.peak_hold -= 1
        else:
            self.peak_value = 0.0


        noise = self.noise * random.uniform(0.8, 1.2)


        # =====================================================
        # 🔥 HEATWAVE SYSTEM
        # =====================================================
        if self.heatwave_force > 0:
            self.heatwave_force *= 0.95

            pressure = self.heatwave_force * 0.018

            soil.surface += pressure
            soil.disturbance += pressure * 0.2

            if self.heatwave_lock > 0:
                self.heatwave_lock -= 1
            else:
                soil.surface -= pressure * 0.25


        # =====================================================
        # 🌪 NORMAL NOISE
        # =====================================================
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
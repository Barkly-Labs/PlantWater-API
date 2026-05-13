import requests
import time
import random
from datetime import datetime, timedelta

SERVER = "http://127.0.0.1:8000"
HEADERS = {"x-api-key": "a6c8768f5533b34dd77409354e0982213e5b0b59f61821fd5902d246a8678567"}

# =========================
# 🌊 DEVICE CONFIG (ESP32)
# =========================
SOIL_WET = 250
SOIL_DRY = 850
IDEAL_SOIL = 520

WATER_ON = 560
WATER_OFF = 500
MIN_SWITCH_TIME = 8

COOLDOWN = 10
MAX_WATER_TIME = 6

# =========================
# 🤖 ESP32 DEVICE CLASS
# =========================
class ESP32Device:
    def __init__(self, bed_id):
        self.bed_id = bed_id

        # "local hardware state"
        self.soil = random.uniform(500, 650)
        self.valve_on = False

        self.last_switch = datetime.utcnow()
        self.last_water = datetime.utcnow()

        self.integral = 0
        self.last_error = 0

    # =========================
    # 📡 SENSOR READ (fake ADC)
    # =========================
    def read_soil(self):
        noise = random.uniform(-3, 3)
        return self.soil + noise

    # =========================
    # 🎛️ CONTROL LOGIC (on-device)
    # =========================
    def compute_pid(self, soil):
        error = soil - IDEAL_SOIL

        if abs(error) < 25:
            return 0

        self.integral += error
        self.integral = max(-800, min(800, self.integral))

        derivative = error - self.last_error
        self.last_error = error

        control = 0.18 * error + 0.001 * self.integral + 0.04 * derivative

        return max(0, min(MAX_WATER_TIME, control))

    # =========================
    # 🌊 VALVE CONTROL (HYSTERESIS)
    # =========================
    def update_valve(self, soil):
        now = datetime.utcnow()

        # 🔒 anti-chatter lock
        if (now - self.last_switch).total_seconds() < MIN_SWITCH_TIME:
            return

        # OFF condition
        if self.valve_on and soil < WATER_OFF:
            self.valve_on = False
            self.last_switch = now
            return

        # ON condition
        if not self.valve_on and soil > WATER_ON:
            duration = self.compute_pid(soil)

            if duration > 0:
                self.valve_on = True
                self.last_switch = now
                self.last_water = now + timedelta(seconds=duration)

    # =========================
    # 💧 WATER EFFECT (local physics)
    # =========================
    def apply_water(self):
        if self.valve_on:
            self.soil -= random.uniform(2, 6)

    # =========================
    # 🌱 LOCAL SOIL EVOLUTION
    # =========================
    def evolve(self):
        evap = random.uniform(0.5, 2.0)
        self.soil += evap

        self.apply_water()

        # clamp
        self.soil = max(SOIL_WET, min(SOIL_DRY, self.soil))

    # =========================
    # 📡 SEND TO SERVER
    # =========================
    def send(self):
        sensors = [self.soil + random.uniform(-2, 2) for _ in range(5)]
        avg = sum(sensors) / len(sensors)

        try:
            requests.post(
                f"{SERVER}/api/bed-data",
                json={
                    "bed_id": self.bed_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "sensors": sensors,
                    "average": avg,
                    "valve_state": "ON" if self.valve_on else "OFF",
                },
                headers=HEADERS,
                timeout=2
            )
        except:
            pass

        print(f"{self.bed_id} | soil:{avg:.1f} | valve:{self.valve_on}")

    # =========================
    # 🔁 ONE ESP32 LOOP
    # =========================
    def loop(self):
        self.evolve()
        self.update_valve(self.soil)
        self.send()

        time.sleep(2)
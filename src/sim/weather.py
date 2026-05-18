import requests
import random
from config import SERVER, HEADERS


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

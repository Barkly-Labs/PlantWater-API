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

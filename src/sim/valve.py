class Valve:
    def __init__(self):
        self.on = False
        self.pressure = 0.0
        self.cooldown = 0

    def update(self, soil):
        self.cooldown = max(0, self.cooldown - 1)

        avg = soil.avg()

        # 🌡 control thresholds (you can tune these later)
        if avg > 710:
            self.on = True
        elif avg < 520 and self.cooldown == 0:
            self.on = False
            self.cooldown = 8

        # 💧 pressure builds when watering
        if self.on:
            self.pressure += 4.0
        else:
            self.pressure *= 0.97

        # 💧 WATERING SHOULD REDUCE DRYNESS
        release = self.pressure * 0.18

        soil.surface -= release   # ✅ FIX (this is the key change)
        soil.root -= release * 0.4 # deeper moisture recovery

        self.pressure -= release
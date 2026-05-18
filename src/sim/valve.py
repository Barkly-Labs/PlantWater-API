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

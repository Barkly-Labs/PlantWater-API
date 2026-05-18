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
            self.stress += 0.08
        elif avg > soil.FIELD_CAPACITY:
            self.stress += 0.04
        else:
            self.stress *= 0.97

        self.stress = max(0, min(10, self.stress))

        if 420 <= avg <= 560:
            self.health += 0.02
        else:
            self.health -= 0.025

        self.health -= self.stress * 0.015
        self.health = max(0, min(100, self.health))

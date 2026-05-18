from asyncio import events
import time
import threading
from weather import Weather
from soil import Soil
from valve import Valve
from plant import Plant
from events import Events
from network import send, heartbeat
from config import TICK_RATE


# =========================================================
# 🔁 MAIN LOOP
# =========================================================
def run():
    weather = Weather()
    soil = Soil()
    valve = Valve()
    plant = Plant()
    events = Events()

    threading.Thread(target=heartbeat, daemon=True).start()

    print("🌿 FIXED GARDEN SIM RUNNING")
    events.test_event("rainburst")

    while True:
        weather.update()

        soil.evaporate(weather)
        soil.flow()
        events.trigger(soil, plant, valve)
        events.apply_noise(soil)

        valve.update(soil)
        soil.equilibrium()
        plant.update(soil)

        send(soil, plant, valve, weather)

        time.sleep(TICK_RATE)


if __name__ == "__main__":
    run()

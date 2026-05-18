import requests
import random
import time
from datetime import datetime, timezone
from config import SERVER, HEADERS, BED_ID
from utils import log


# =========================================================
# 📡 SEND
# =========================================================
def send(soil, plant, valve, weather):
    avg = soil.avg()

    sensors = [avg + random.uniform(-2.5, 2.5) for _ in range(5)]

    try:
        requests.post(
            f"{SERVER}/api/bed-data",
            json={
                "bed_id": BED_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "average": avg,
                "sensors": sensors,
                "valve_state": "ON" if valve.on else "OFF",
                "plant_health": plant.health,
                "weather": {
                    "temp": weather.temp,
                    "humidity": weather.humidity,
                    "sun": weather.sun
                },
                "rssi": int(random.uniform(-70, -40)),
            },
            headers=HEADERS,
            timeout=2
        )
    except:
        pass

    log(f"SOIL {avg:.1f} | VALVE {valve.on} | HEALTH {plant.health:.1f}")


# =========================================================
# 💓 HEARTBEAT
# =========================================================
def heartbeat():
    while True:
        try:
            requests.post(
                f"{SERVER}/api/node/heartbeat",
                params={"bed_id": BED_ID},
                headers=HEADERS,
                timeout=2
            )
        except:
            pass
        time.sleep(10)

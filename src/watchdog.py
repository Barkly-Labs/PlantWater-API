import threading
import time
import requests
from fastapi import requests


def api_watchdog():
    global last_api_online

    while True:
        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=5)
            online = r.status_code == 200
        except:
            online = False

        # API just went DOWN
        if last_api_online and not online:
            queue_all("🚨 Smart Garden API OFFLINE")

        # API just came BACK
        if not last_api_online and online:
            queue_all("🟢 Smart Garden API BACK ONLINE")

        last_api_online = online
        time.sleep(10)
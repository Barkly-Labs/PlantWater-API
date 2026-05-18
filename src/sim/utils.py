from datetime import datetime
import os
from config import LOG_FILE


# =========================================================
# 🪵 LOGGING
# =========================================================
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

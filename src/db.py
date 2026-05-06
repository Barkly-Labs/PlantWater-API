"""
Database Configuration & Global State Management
Centralized database setup, sessions, and in-memory caches
"""

import threading
import time
from datetime import datetime
from typing import Dict
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """
    Dependency function to provide database session to route handlers.

    Creates a new database session for each request, ensuring proper
    resource management with automatic cleanup in a finally block.

    Yields:
        Session: SQLAlchemy session for database operations
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# WEATHER CONFIGURATION & CACHING
# ============================================================
OPENWEATHER_API_KEY = "e88c64c56baab21c5eeff4def1c026be"
CITY = "Detroit,US"

weather_cache = {
    "last_update": None,
    "data": None,
}

_weather_cache = {
    "data": None,
    "last_update": 0
}

global_weather = {"will_rain": False, "raw": None, "last_update": None}


# ============================================================
# IN-MEMORY STATE (IRRIGATION & SENSOR DATA)
# ============================================================
valve_history = defaultdict(list)
watering_sessions = {}
lifetime_stats_store = {}
rain_memory = {}
bed_state = {}
last_watered = {}
rain_pause = {}
active_valves = {}
node_last_seen = {}


# ============================================================
# BACKGROUND WEATHER LOOP
# ============================================================
def weather_loop():
    """Background thread that updates global weather every minute"""
    # Import here to avoid circular dependencies
    from routes.beds import current_weather
    
    while True:
        try:
            w = current_weather()
            global_weather["raw"] = w
            global_weather["last_update"] = datetime.utcnow()
        except:
            pass
        time.sleep(60)


def start_weather_thread():
    """Start the background weather update thread"""
    threading.Thread(target=weather_loop, daemon=True).start()

"""
Bed Sensor & IoT Routes
All /api/beds/*, /api/config/*, /api/weather/*, and related endpoints
"""

from datetime import datetime, timedelta
import time
import requests
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from db import (
    get_db, OPENWEATHER_API_KEY, CITY, weather_cache, _weather_cache,
    global_weather, valve_history, active_valves, rain_pause, last_watered,
    rain_memory, watering_sessions, lifetime_stats_store, node_last_seen
)
from models import BedReading, BedMetaDB, BedConfigDB, User
from schemas import BedData, BedConfig
from services.notifications import send_notification

router = APIRouter()

API_KEY = "your_super_secret_key"
OFFLINE_SECONDS = 15


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key header"""
    from fastapi import HTTPException
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def is_rain_spike(bed_id, current, previous):
    """Detect sudden spike in moisture (rain event)"""
    if previous is None:
        return False
    return (current - previous) > 120


def calculate_health(moisture_values, rssi_values):
    """Calculate plant health score from sensor data"""
    if not moisture_values:
        return 0

    RAW_MIN = 200
    RAW_MAX = 800
    ideal = 60

    def normalize(v):
        return max(0, min(100, (v - RAW_MIN) / (RAW_MAX - RAW_MIN) * 100))

    normalized = [normalize(v) for v in moisture_values]
    avg = sum(normalized) / len(normalized)

    # Moisture score
    distance = abs(ideal - avg)
    moisture_score = 100 - (distance ** 1.3) * 1.4
    moisture_score = max(0, min(100, moisture_score))

    # Stability score
    if len(normalized) > 1:
        diffs = [abs(normalized[i] - normalized[i + 1]) for i in range(len(normalized) - 1)]
        variance = sum(diffs) / len(diffs)
    else:
        variance = 0
    stability_score = max(0, 100 - variance * 2.5)

    # Signal score
    if rssi_values:
        avg_rssi = sum(rssi_values) / len(rssi_values)
        signal_score = max(0, min(100, 100 + avg_rssi))
    else:
        signal_score = 70

    health = (
        moisture_score * 0.65 +
        stability_score * 0.20 +
        signal_score * 0.15
    )

    return max(0, min(100, health))


def current_weather():
    """Fetch current weather from OpenWeather API"""
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
    )

    r = requests.get(url)
    data = r.json()

    weather_main = data["weather"][0]["main"]
    rain = data.get("rain", {}).get("1h", 0)
    clouds = data.get("clouds", {}).get("all", 0)
    sun = max(0, 100 - clouds)

    return {
        "current": weather_main,
        "is_raining_now": weather_main.lower() == "rain",
        "temp": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "rain": rain,
        "sun": sun,
    }


def get_weather():
    """Get weather with caching"""
    now = datetime.utcnow()

    if weather_cache["last_update"]:
        if now - weather_cache["last_update"] < timedelta(minutes=10):
            return weather_cache["data"]

    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
    )

    r = requests.get(url)
    data = r.json()

    will_rain = any(item.get("pop", 0) > 0.5 for item in data.get("list", [])[:6])

    result = {"will_rain": bool(will_rain), "last_update": now.isoformat()}

    weather_cache["last_update"] = now
    weather_cache["data"] = result

    return result


# ============================================================
# SENSOR DATA ENDPOINTS
# ============================================================

@router.post("/api/bed-data", dependencies=[Depends(verify_api_key)], tags=["Beds"])
def receive_data(data: BedData, db: Session = Depends(get_db)):
    """Accept and store sensor readings from ESP32 microcontroller."""
    try:
        weather = global_weather["raw"]

        reading = BedReading(
            bed_id=data.bed_id,
            timestamp=datetime.fromisoformat(data.timestamp),
            average=data.average,
            valve_state=data.valve_state,
            rssi=data.rssi,
            sensors=data.sensors,
            weather=weather,
            plant_health=calculate_health(
                data.sensors,
                [data.rssi] if data.rssi is not None else None
            )
        )

        db.add(reading)
        db.commit()

        # ============================================================
        # 🌿 LOOKUP USER (IMPORTANT FIX)
        # ============================================================
        meta = (
            db.query(BedMetaDB)
            .filter(BedMetaDB.bed_id == data.bed_id)
            .first()
        )

        user_id = meta.user_id if meta else None

        # ============================================================
        # 🚨 NOTIFICATIONS
        # ============================================================
        if user_id:

            # 🚨 Dry soil alert
            if data.average > 700:
                send_notification(
                    user_id=user_id,
                    message=f"🚨 Bed {data.bed_id}: Soil is very dry ({data.average})",
                    db=db,
                    n_type="alert"
                )

            # 🌱 Healthy range info
            elif data.average < 300:
                send_notification(
                    user_id=user_id,
                    message=f"🌿 Bed {data.bed_id}: Soil moisture is healthy",
                    db=db,
                    n_type="info"
                )

            # 📡 Sensor instability warning
            if data.rssi is not None and data.rssi < -80:
                send_notification(
                    user_id=user_id,
                    message=f"⚠️ Bed {data.bed_id}: Weak signal (RSSI {data.rssi})",
                    db=db,
                    n_type="error"
                )

        return {"status": "ok"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================================
# BEDS QUERY ENDPOINTS
# ============================================================

@router.get("/api/beds", tags=["Beds"])
def get_beds(db: Session = Depends(get_db)):
    """Retrieve the latest sensor reading for each plant bed."""
    beds = {}
    rows = db.query(BedReading).order_by(BedReading.timestamp.desc()).all()

    for r in rows:
        if r.bed_id not in beds:
            beds[r.bed_id] = {
                "bed_id": r.bed_id,
                "timestamp": r.timestamp,
                "average": r.average,
                "valve_state": r.valve_state,
                "rssi": r.rssi,
                "sensors": r.sensors,
            }

    return beds


@router.get("/api/beds/{bed_id}/history", tags=["Beds"])
def history(bed_id: str, db: Session = Depends(get_db)):
    """Retrieve recent historical readings for a specific plant bed."""
    rows = (
        db.query(BedReading)
        .filter(BedReading.bed_id == bed_id)
        .order_by(BedReading.timestamp.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "timestamp": r.timestamp,
            "average": r.average,
            "valve_state": r.valve_state,
            "sensors": r.sensors,
        }
        for r in rows
    ]


@router.get("/api/beds/{bed_id}/range", tags=["Beds"])
def get_range(
    bed_id: str, start: datetime, end: datetime, db: Session = Depends(get_db)
):
    """Retrieve sensor readings within a specific time range."""
    rows = (
        db.query(BedReading)
        .filter(BedReading.bed_id == bed_id)
        .filter(BedReading.timestamp >= start)
        .filter(BedReading.timestamp <= end)
        .order_by(BedReading.timestamp.asc())
        .all()
    )

    return [
        {
            "timestamp": r.timestamp,
            "average": r.average,
            "valve_state": r.valve_state,
        }
        for r in rows
    ]


@router.get("/api/beds/{bed_id}/graph", tags=["Beds"])
def graph_data(bed_id: str, limit: int = 200, db: Session = Depends(get_db)):
    """Retrieve sensor data formatted for frontend charting libraries."""
    rows = (
        db.query(BedReading)
        .filter(BedReading.bed_id == bed_id)
        .order_by(BedReading.timestamp.desc())
        .limit(limit)
        .all()
    )

    rows.reverse()

    return {
        "timestamps": [r.timestamp for r in rows],
        "average": [r.average for r in rows],
        "valve": [r.valve_state for r in rows],
    }


@router.get("/api/beds/{bed_id}/stats", tags=["Beds"])
def stats(bed_id: str, db: Session = Depends(get_db)):
    """Calculate aggregated statistics for a plant bed's moisture data."""
    rows = db.query(BedReading).filter(BedReading.bed_id == bed_id).all()

    if not rows:
        return {"error": "no data"}

    vals = [r.average for r in rows]

    return {
        "count": len(vals),
        "min": min(vals),
        "max": max(vals),
        "avg": sum(vals) / len(vals),
        "last": vals[-1],
    }


@router.get("/api/beds/latest", tags=["Beds"])
def latest(db: Session = Depends(get_db)):
    """Get latest reading for each active bed (online detection)."""
    now = datetime.utcnow()
    subquery = db.query(BedReading).order_by(BedReading.timestamp.desc()).all()

    seen = {}
    active = {}

    for r in subquery:
        if r.bed_id in seen:
            continue
        seen[r.bed_id] = True

        if not r.timestamp:
            continue

        age = (now - r.timestamp).total_seconds()

        if age > OFFLINE_SECONDS:
            continue

        live = active_valves.get(r.bed_id)

        if live and now <= live["until"]:
            valve_state = "ON"
        else:
            valve_state = r.valve_state

        active[r.bed_id] = {
            "bed_id": r.bed_id,
            "average": r.average,
            "valve_state": valve_state,
            "rssi": r.rssi,
            "ip": getattr(r, "ip", None),
            "timestamp": r.timestamp,
            "age": age
        }

    return active


@router.get("/api/beds/{bed_id}/full-graph", tags=["Irrigation"])
def full_graph(bed_id: str, limit: int = 200, db: Session = Depends(get_db)):
    """Get detailed graph data including health and RSSI."""
    rows = (
        db.query(BedReading)
        .filter(BedReading.bed_id == bed_id)
        .order_by(BedReading.timestamp.desc())
        .limit(limit)
        .all()
    )

    rows.reverse()

    timestamps = []
    moisture = []
    valve = []
    rssi = []
    plant_health = []

    for r in rows:
        timestamps.append(r.timestamp.isoformat() if r.timestamp else "")
        moisture.append(r.average if r.average is not None else 0)
        valve.append(1 if r.valve_state == "ON" else 0)

        try:
            rssi_val = float(r.rssi) if r.rssi is not None else -100
        except:
            rssi_val = -100
        rssi.append(rssi_val)

        try:
            plant_health.append(round(r.plant_health, 1) if r.plant_health is not None else 0)
        except:
            plant_health.append(0)

    return {
        "timestamps": timestamps,
        "moisture": moisture,
        "rain": [0] * len(timestamps),
        "valve": valve,
        "rssi": rssi,
        "plant_health": plant_health
    }


# ============================================================
# CONFIGURATION ENDPOINTS
# ============================================================

@router.get("/api/config/{bed_id}", tags=["System"])
def get_config(bed_id: str, db: Session = Depends(get_db)):
    """Retrieve current configuration settings for a plant bed."""
    config = db.query(BedConfigDB).filter(BedConfigDB.bed_id == bed_id).first()

    if not config:
        config = BedConfigDB(bed_id=bed_id)
        db.add(config)
        db.commit()
        db.refresh(config)

    return {
        "bed_id": bed_id,
        "moisture_threshold": config.moisture_threshold,
        "watering_duration_sec": config.watering_duration_sec,
        "cooldown_sec": config.cooldown_sec,
        "sampling_interval_sec": config.sampling_interval_sec,
    }


@router.post("/api/config/{bed_id}", dependencies=[Depends(verify_api_key)], tags=["System"])
def update_config(bed_id: str, config: BedConfig, db: Session = Depends(get_db)):
    """Update configuration settings for a plant bed."""
    db_config = db.query(BedConfigDB).filter(BedConfigDB.bed_id == bed_id).first()

    if not db_config:
        db_config = BedConfigDB(bed_id=bed_id)
        db.add(db_config)

    for k, v in config.model_dump(exclude_unset=True).items():
        setattr(db_config, k, v)

    db.commit()

    return {"status": "updated"}


# ============================================================
# WATERING DECISION ENDPOINTS
# ============================================================

@router.post("/api/should-water", dependencies=[Depends(verify_api_key)], tags=["Control"])
def should_water(bed_id: str, average_moisture: float, db: Session = Depends(get_db)):
    """Intelligent watering decision engine."""
    now = datetime.utcnow()

    config = db.query(BedConfigDB).filter(BedConfigDB.bed_id == bed_id).first()

    if not config:
        config = BedConfigDB(bed_id=bed_id)
        db.add(config)
        db.commit()
        db.refresh(config)

    soil_dry = average_moisture > config.moisture_threshold
    weather = current_weather()
    rain_expected = weather["is_raining_now"]

    water = soil_dry and not rain_expected

    if weather["is_raining_now"]:
        rain_pause[bed_id] = now + timedelta(minutes=30)

    if now < rain_pause.get(bed_id, datetime.min):
        return {"water": False}

    last = last_watered.get(bed_id)

    if last and (now - last).total_seconds() < config.cooldown_sec:
        return {"water": False}

    if water:
        active_valves[bed_id] = {
            "state": "ON",
            "until": now + timedelta(seconds=config.watering_duration_sec),
        }
    else:
        if bed_id not in active_valves:
            active_valves[bed_id] = {"state": "OFF", "until": now}

    return {
        "bed_id": bed_id,
        "water": water,
        "soil_dry": soil_dry,
        "rain_expected": rain_expected,
        "weather": weather,
        "valve_state": active_valves.get(bed_id, {}).get("state", "OFF"),
    }


@router.post("/api/water", tags=["Irrigation"], dependencies=[Depends(verify_api_key)])
def water_bed(bed_id: str, duration: int = 3):
    """Manually control valve irrigation."""
    now = datetime.utcnow()
    active_valves[bed_id] = {"state": "ON", "until": now + timedelta(seconds=duration)}

    return {"bed_id": bed_id, "valve_state": "ON", "duration": duration}


@router.get("/api/valve/{bed_id}", tags=["Irrigation"])
def valve_status(bed_id: str):
    """Get current valve status."""
    now = datetime.utcnow()
    v = active_valves.get(bed_id)

    if not v:
        return {"bed_id": bed_id, "valve_state": "OFF"}

    if now > v["until"]:
        active_valves.pop(bed_id, None)
        return {"bed_id": bed_id, "valve_state": "OFF"}

    return {"bed_id": bed_id, "valve_state": "ON"}


@router.post("/api/beds/{bed_id}/mode", tags=["Irrigation"], dependencies=[Depends(verify_api_key)])
def set_mode(bed_id: str, mode: str):
    """Set bed operating mode."""
    active_valves.setdefault(bed_id, {})
    active_valves[bed_id]["mode"] = mode

    return {"bed_id": bed_id, "mode": mode}


@router.get("/api/beds/{bed_id}/mode", tags=["Irrigation"])
def get_mode(bed_id: str):
    """Get bed operating mode."""
    return {
        "bed_id": bed_id,
        "mode": active_valves.get(bed_id, {}).get("mode", "normal"),
    }


# ============================================================
# WATERING CYCLE TRACKING
# ============================================================

@router.post("/api/beds/{bed_id}/water-cycle", dependencies=[Depends(verify_api_key)], tags=["Irrigation"])
def water_cycle(bed_id: str, valve_state: str):
    """Track watering cycle for lifetime stats."""
    now = datetime.utcnow()

    if bed_id not in lifetime_stats_store:
        lifetime_stats_store[bed_id] = {"times_watered": 0, "total_seconds": 0}

    if bed_id not in watering_sessions:
        watering_sessions[bed_id] = None

    if valve_state == "ON":
        if watering_sessions[bed_id] is None:
            watering_sessions[bed_id] = {"start": now}

        return {"bed_id": bed_id, "state": "started"}

    if valve_state == "OFF":
        session = watering_sessions.get(bed_id)

        if session is not None:
            duration = (now - session["start"]).total_seconds()

            lifetime_stats_store[bed_id]["times_watered"] += 1
            lifetime_stats_store[bed_id]["total_seconds"] += duration

            watering_sessions[bed_id] = None

            return {"bed_id": bed_id, "state": "stopped", "duration_sec": duration}

        return {"bed_id": bed_id, "state": "ignored_no_session"}

    return {"bed_id": bed_id, "state": "no_change"}


@router.get("/api/beds/{bed_id}/lifetime", tags=["Irrigation"])
def lifetime_stats(bed_id: str, db: Session = Depends(get_db)):
    """Get lifetime watering statistics from database."""
    rows = (
        db.query(BedReading)
        .filter(BedReading.bed_id == bed_id)
        .order_by(BedReading.timestamp.asc())
        .all()
    )

    if not rows:
        return {"error": "no data"}

    water_events = 0
    last_state = "OFF"
    last_watered_time = None
    total_on_time = timedelta(0)
    last_on_time = None

    for r in rows:
        if r.valve_state == "ON" and last_state != "ON":
            water_events += 1
            last_on_time = r.timestamp
            last_watered_time = r.timestamp

        if r.valve_state == "OFF" and last_state == "ON":
            if last_on_time:
                total_on_time += r.timestamp - last_on_time
                last_on_time = None

        last_state = r.valve_state

    return {
        "bed_id": bed_id,
        "times_watered": water_events,
        "last_watered": last_watered_time,
        "total_watering_minutes": round(total_on_time.total_seconds() / 60, 2),
        "avg_moisture": sum(r.average for r in rows) / len(rows),
    }


# ============================================================
# BED METADATA ENDPOINTS
# ============================================================

@router.post("/api/beds/{bed_id}/meta", tags=["System"])
def save_bed_meta(bed_id: str, data: dict, db: Session = Depends(get_db)):
    """Save bed metadata (name, icon)."""
    from fastapi import Body
    
    row = db.query(BedMetaDB).filter(BedMetaDB.bed_id == bed_id).first()

    if not row:
        row = BedMetaDB(bed_id=bed_id)
        db.add(row)

    row.name = data.get("name", bed_id)
    row.icon = data.get("icon", "🌱")

    db.commit()
    db.refresh(row)

    return {"ok": True, "bed_id": bed_id, "meta": {"name": row.name, "icon": row.icon}}


@router.get("/api/beds/{bed_id}/meta", tags=["System"])
def get_bed_meta(bed_id: str, db: Session = Depends(get_db)):
    """Get bed metadata."""
    row = db.query(BedMetaDB).filter(BedMetaDB.bed_id == bed_id).first()

    if not row:
        return {"bed_id": bed_id, "name": bed_id, "icon": "🌱"}

    return {"bed_id": bed_id, "name": row.name, "icon": row.icon}


@router.get("/api/beds/meta", tags=["System"])
def get_all_bed_meta(db: Session = Depends(get_db)):
    """Get all bed metadata."""
    rows = db.query(BedMetaDB).all()

    return {r.bed_id: {"name": r.name, "icon": r.icon} for r in rows}


# ============================================================
# HEALTH & ML ENDPOINTS
# ============================================================

@router.get("/api/beds/{bed_id}/health", tags=["ML"])
def get_bed_health(bed_id: str, db: Session = Depends(get_db)):
    """Get plant health status."""
    latest = (
        db.query(BedReading)
        .filter(BedReading.bed_id == bed_id)
        .order_by(BedReading.timestamp.desc())
        .first()
    )

    if not latest:
        return {
            "bed_id": bed_id,
            "health": None,
            "avg_moisture": None,
            "status": "unknown"
        }

    health_value = latest.plant_health or 0

    status = (
        "healthy" if health_value > 75
        else "warning" if health_value > 45
        else "bad"
    )

    return {
        "bed_id": bed_id,
        "health": health_value,
        "avg_moisture": latest.average,
        "status": status
    }


@router.get("/api/beds/{bed_id}/risk", tags=["ML"])
def bed_risk_next_hour(bed_id: str, db: Session = Depends(get_db)):
    """Predict risk of drying in next hour."""
    rows = (
        db.query(BedReading)
        .filter(BedReading.bed_id == bed_id)
        .order_by(BedReading.timestamp.desc())
        .limit(30)
        .all()
    )

    if not rows:
        return {
            "bed_id": bed_id,
            "risk_next_hour": "unknown",
            "confidence": 0,
            "time_to_dry_minutes": None
        }

    moisture = [r.average for r in rows if r.average is not None]

    if len(moisture) < 5:
        return {
            "bed_id": bed_id,
            "risk_next_hour": "low",
            "confidence": 0.3,
            "time_to_dry_minutes": None
        }

    moisture = moisture[::-1]

    n = len(moisture)
    x = list(range(n))

    x_mean = sum(x) / n
    y_mean = sum(moisture) / n

    numerator = sum((x[i] - x_mean) * (moisture[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n)) + 1e-6

    slope = numerator / denominator

    if slope < -2:
        risk = "high"
        confidence = 0.85
    elif slope < -0.5:
        risk = "medium"
        confidence = 0.65
    else:
        risk = "low"
        confidence = 0.55

    current = moisture[-1]
    dry_threshold = 650

    if slope < 0:
        time_to_dry = (dry_threshold - current) / abs(slope)
        time_to_dry_minutes = max(0, int(time_to_dry * 10))
    else:
        time_to_dry_minutes = None

    print(f"DEBUG: Bed {bed_id} - Slope: {slope:.3f}, Risk: {risk}, Time to Dry: {time_to_dry_minutes} mins")

    return {
        "bed_id": bed_id,
        "risk_next_hour": risk,
        "confidence": round(confidence, 2),
        "time_to_dry_minutes": time_to_dry_minutes,
        "slope": round(slope, 3)
    }


# ============================================================
# SYSTEM & WEATHER ENDPOINTS
# ============================================================

@router.get("/health", tags=["System"])
def health():
    """Health check endpoint for monitoring."""
    return {"status": "alive"}


@router.delete("/api/cleanup", dependencies=[Depends(verify_api_key)], tags=["System"])
def cleanup(db: Session = Depends(get_db)):
    """Delete historical data older than 7 days."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    db.query(BedReading).filter(BedReading.timestamp < cutoff).delete()
    db.commit()

    return {"status": "cleaned"}


@router.get("/api/will-rain", tags=["Weather"])
def weather_api():
    """Check if rain is expected."""
    return get_weather()


@router.get("/api/weather/current", tags=["Weather"])
def weather_current():
    """Get current weather."""
    return current_weather()


@router.get("/api/weather", tags=["System"])
def weather_summary():
    """Get cached weather summary."""
    now = time.time()

    if _weather_cache["data"] is None or now - _weather_cache["last_update"] > 300:
        weather = current_weather()

        _weather_cache["data"] = {
            "temp": weather.get("temp"),
            "humidity": weather.get("humidity"),
            "is_raining_now": weather.get("is_raining_now"),
            "will_rain": weather.get("will_rain"),
        }

        _weather_cache["last_update"] = now

    return _weather_cache["data"]


@router.get("/api/system/overview", tags=["System"])
def system_overview(db: Session = Depends(get_db)):
    """Get system status at a glance."""
    rows = db.query(BedReading).order_by(BedReading.timestamp.desc()).all()

    latest = {}
    for r in rows:
        if r.bed_id not in latest:
            latest[r.bed_id] = r

    total = len(latest)
    dry = 0
    watering = 0

    for b in latest.values():
        if b.average > 700:
            dry += 1

        live = active_valves.get(b.bed_id)
        if live and live.get("state") == "ON":
            watering += 1

    return {
        "total_beds": total,
        "dry_beds": dry,
        "watering_beds": watering,
        "healthy_beds": total - dry,
    }


# ============================================================
# NODE HEARTBEAT ENDPOINT
# ============================================================

@router.post("/api/node/heartbeat", tags=["System"])
def node_heartbeat(bed_id: str = Query(...), ip: str = Query(None), rssi: int = Query(None)):
    """Record node heartbeat and connectivity info."""
    now = datetime.utcnow().isoformat()

    node_last_seen[bed_id] = {
        "bed_id": bed_id,
        "ip": ip,
        "rssi": rssi,
        "last_seen": now,
    }

    return {"ok": True, "bed_id": bed_id, "last_seen": now}


@router.get("/api/beds/{bed_id}/history", tags=["Beds"])
def get_history(bed_id: str, db: Session = Depends(get_db)):
    return (
        db.query(BedData)
        .filter(BedData.bed_id == bed_id)
        .order_by(BedData.timestamp.desc())
        .limit(100)
        .all()
    )

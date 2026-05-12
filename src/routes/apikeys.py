from datetime import datetime, timedelta
import time
import requests
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from auth import generate_raw_key, hash_key
from db import (
    get_db, OPENWEATHER_API_KEY, CITY, weather_cache, _weather_cache,
    global_weather, valve_history, active_valves, rain_pause, last_watered,
    rain_memory, watering_sessions, lifetime_stats_store, node_last_seen
)
import db
from models import APIKey, BedReading, BedMetaDB, BedConfigDB, User
from auth import verify_api_key
from schemas import BedData, BedConfig
from deps  import get_current_user

from services.notifications import  send_notification, should_alert

router = APIRouter()

@router.post("/api/keys/create", tags=["API Keys"])
def create_key(name: str,db: Session = Depends(get_db),):
    raw = generate_raw_key()
    hashed = hash_key(raw)

    key = APIKey(
        name=name,
        key_hash=hashed
    )

    db.add(key)
    db.commit()

    return {
        "name": name,
        "api_key": raw  # ONLY shown once
    }


@router.get("/api/keys", tags=["API Keys"])
def list_keys(_=Depends(verify_api_key),db: Session = Depends(get_db)):
    keys = db.query(APIKey).all()

    return [
        {
            "id": k.id,
            "name": k.name,
            "active": k.active,
            "created_at": k.created_at
        }
        for k in keys
    ]

@router.post("/api/keys/{key_id}/revoke", tags=["API Keys"])
def revoke_key(key_id: str, _=Depends(verify_api_key),db: Session = Depends(get_db)):
    key = db.query(APIKey).filter_by(id=key_id).first()

    if not key:
        return {"error": "not found"}

    key.active = False
    db.commit()

    return {"status": "revoked"}
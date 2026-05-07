"""
Pydantic Models for Request/Response Validation
Data schemas for API endpoints and form submissions
"""

from typing import List, Optional
from pydantic import BaseModel

from carriers import Carrier


# ============================================================
# SENSOR DATA MODELS
# ============================================================
class BedData(BaseModel):
    """Schema for incoming sensor readings from ESP32"""
    bed_id: str
    timestamp: str
    sensors: List[float]
    average: float
    valve_state: str
    rssi: Optional[int] = None
    plant_health: Optional[float] = None


class BedConfig(BaseModel):
    """Schema for updating plant bed configuration settings"""
    moisture_threshold: Optional[int] = None
    watering_duration_sec: Optional[int] = None
    cooldown_sec: Optional[int] = None
    sampling_interval_sec: Optional[int] = None


# ============================================================
# AUTHENTICATION MODELS
# ============================================================
class RegisterRequest(BaseModel):
    """Registration request payload"""
    email: str
    password: str


class LoginRequest(BaseModel):
    """Login request payload"""
    email: str
    password: str


# ============================================================
# USER CONTACT MODELS
# ============================================================
class ContactRequest(BaseModel):
    """User contact information for SMS alerts"""
    phone: str
    carrier: str


# ============================================================
# SYSTEM MODELS
# ============================================================
class Heartbeat(BaseModel):
    """Node heartbeat ping"""
    bed_id: str


class AlertRequest(BaseModel):
    user_id: int
    message: str

class ContactUpdate(BaseModel):
    phone: str
    carrier: Carrier
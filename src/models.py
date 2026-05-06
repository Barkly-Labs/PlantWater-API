"""
SQLAlchemy ORM Models
Database table definitions for beds, readings, configurations, and users
"""

from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Column, Integer, String, Float, DateTime, JSON

from db import Base


# ============================================================
# BED METADATA MODEL
# ============================================================
class BedMetaDB(Base):
    """Stores metadata for plant beds (name, icon) for display purposes"""
    __tablename__ = "bed_meta"

    id = Column(Integer, primary_key=True)
    bed_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, default="")
    icon = Column(String, default="🌱")
    ip = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))


# ============================================================
# BED SENSOR READINGS MODEL
# ============================================================
class BedReading(Base):
    """
    ORM model for storing plant bed sensor readings.

    Represents a single snapshot of sensor data from a plant bed,
    including moisture levels, valve state, and signal strength.
    """
    __tablename__ = "bed_readings"

    id = Column(Integer, primary_key=True)
    bed_id = Column(String, index=True)
    timestamp = Column(DateTime)
    average = Column(Float)
    valve_state = Column(String)
    weather = Column(JSON, nullable=True)
    rssi = Column(Integer)
    sensors = Column(JSON)
    plant_health = Column(Float, nullable=True)


# ============================================================
# BED CONFIGURATION MODEL
# ============================================================
class BedConfigDB(Base):
    """
    ORM model for storing plant bed configuration settings.

    Manages configurable parameters for the automated irrigation system,
    such as moisture thresholds and valve timing settings.
    """
    __tablename__ = "bed_config"

    id = Column(Integer, primary_key=True)
    bed_id = Column(String, unique=True)
    moisture_threshold = Column(Integer, default=600)
    watering_duration_sec = Column(Integer, default=3)
    cooldown_sec = Column(Integer, default=30)
    sampling_interval_sec = Column(Integer, default=10)
    user_id = Column(Integer, ForeignKey("users.id"))


# ============================================================
# USER MODEL
# ============================================================
class User(Base):
    """User account model for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(String)
    phone_number = Column(String)
    carrier = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# USER CONTACT MODEL
# ============================================================
class UserContact(Base):
    """User contact info for SMS/notification delivery"""
    __tablename__ = "user_contacts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, index=True)
    phone = Column(String)
    carrier = Column(String)

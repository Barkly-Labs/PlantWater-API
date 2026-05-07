"""
Smart Irrigation System API - Main Application
FastAPI application initialization and router setup
"""

from fastapi import FastAPI

# Import database and models to initialize them
from db import Base, engine, start_weather_thread
from models import User, UserContact, BedReading, BedConfigDB, BedMetaDB

# Import routers
from routes.beds import router as beds_router
from routes.users import router as users_router
from routes.pages import router as pages_router
from routes.sms import router as sms_router
from routes.dis import router as discord_router 
# ============================================================
# DATABASE INITIALIZATION
# ============================================================
# Create all database tables
Base.metadata.create_all(bind=engine)

# ============================================================
# FASTAPI APPLICATION SETUP
# ============================================================
app = FastAPI(
    title="Smart Irrigation System",
    docs_url="/docs",
    openapi_tags=[
        {"name": "System", "description": "Health, overview, nodes"},
        {"name": "Beds", "description": "Bed data, stats, graphs"},
        {"name": "Control", "description": "Watering and valves"},
        {"name": "Weather", "description": "Weather and rain prediction"},
        {"name": "Irrigation", "description": "Endpoints related to watering control and valve status"},
        {"name": "ML", "description": "Endpoints for machine learning model predictions and training"},
        {"name": "SMS", "description": "Endpoints for SMS alert management"},
        {"name": "Auth", "description": "User authentication endpoints"},
        {"name": "Pages", "description": "HTML page routes"},
        {"name": "Discord", "description": "Endpoints for Discord integration and OAuth callbacks"}
    ]
)

# ============================================================
# INCLUDE ROUTERS
# ============================================================
# Include all routers from modular route files
app.include_router(beds_router)
app.include_router(users_router)
app.include_router(pages_router)
app.include_router(sms_router)
app.include_router(discord_router)  # Discord router
# ============================================================
# BACKGROUND TASKS
# ============================================================
# Start the background weather update thread
start_weather_thread()

# ============================================================
# LIFESPAN (if needed for startup/shutdown logic)
# ============================================================
# Currently using background threads; can extend with lifespan in FastAPI 0.93+


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

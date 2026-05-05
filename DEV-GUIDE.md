# 📋 PlantWater Development Guide & TODO

Complete guide for developing, maintaining, and extending the PlantWater API system.

---

## 🎯 Project Goals

**Core Mission:**
Create a fully autonomous, weather-aware smart irrigation system that:
- Monitors soil moisture in real-time
- Makes intelligent watering decisions
- Tracks plant health and system performance
- Integrates with multiple platforms (Discord, web dashboards, mobile)
- Requires minimal user intervention

**Target Users:**
- Home gardeners (hobby scale, 2-10 beds)
- Greenhouse operators
- Agricultural researchers
- IoT enthusiasts

---

## 🏗️ Architecture Overview

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API** | FastAPI (Python) | RESTful backend, weather integration |
| **Database** | SQLite | Persistent sensor data + configs |
| **Frontend** | HTML/CSS/JS (embedded) | Dashboard + graphs |
| **Discord Bot** | discord.py | Chat interface + alerts |
| **Simulator** | Python | Testing without hardware |
| **Hardware** | ESP32 | WiFi-enabled soil sensors |
| **ML** | scikit-learn | Plant health prediction (future) |

### Data Flow

```
ESP32 Sensors
    ↓
POST /api/bed-data
    ↓
FastAPI Server (main.py)
    ↓
SQLite Database (bed_readings)
    ↓
GET /api/beds/{bed_id}/...
    ↓
Frontend / Discord Bot / Mobile App
```

### Decision Flow

```
New Sensor Reading
    ↓
/api/should-water endpoint
    ↓
[Check Config] [Check Weather] [Check Cooldown]
    ↓
Decision: Water? YES/NO
    ↓
If YES → Signal valve to open
If NO  → Log decision reason
    ↓
Update plant_health score
```

---

## 📋 Development TODO List

### Phase 1: Core Functionality (Mostly Complete ✅)

- [x] FastAPI server scaffold
- [x] SQLite database setup
- [x] Bed reading ingestion (`POST /api/bed-data`)
- [x] Basic query endpoints (history, stats, graph)
- [x] Configuration management
- [x] Weather integration (OpenWeather API)
- [x] Watering decision logic
- [x] Valve control simulation
- [x] Simulator for testing
- [x] Discord bot integration
- [x] Plant health tracking
- [x] Lifetime statistics

### Phase 2: Features & Polish (In Progress 🟡)

#### High Priority

- [ ] **SMS Alerts** - Send text messages for critical plant health
  - Implementation: Twilio integration
  - When: Plant health < 20% OR moisture > 900
  - Frequency: Once per 4 hours max

- [ ] **API Key Security** - Add API key management UI
  - Implementation: Generate/revoke keys in database
  - Store hashed keys (bcrypt)
  - Log key usage for audit trail

- [ ] **Multi-Location Support** - Run multiple server instances
  - Implementation: Add location_id to all readings
  - Allow different configs per location
  - Unified dashboard view

- [ ] **Enhanced Dashboard UX**
  - Redesign historical data page
  - Add real-time WebSocket updates
  - Better mobile responsiveness
  - Dark mode toggle

#### Medium Priority

- [ ] **IP Address Tracking** - Display ESP32 device IPs
  - Implementation: Store IP in bed_meta table
  - Show on device management page
  - Ping to verify connectivity

- [ ] **Plant Health Prediction** - ML-based forecasting
  - Implementation: scikit-learn RandomForestClassifier
  - Train on historical data
  - Predict health 24h ahead

- [ ] **Data Export** - CSV/JSON export functionality
  - Implementation: Generate exports on demand
  - Support date range filtering
  - Email delivery option

- [ ] **Webhook Integration** - Send data to external services
  - Implementation: HTTP POST to user-provided URLs
  - Support filters (e.g., "only alert on watering")
  - Retry logic for failed requests

#### Low Priority

- [ ] **Mobile App** - React Native or Flutter
  - Feature parity with web dashboard
  - Push notifications
  - Offline caching

- [ ] **PostgreSQL Support** - Scale beyond SQLite
  - Implementation: SQLAlchemy abstraction
  - Migration scripts
  - Connection pooling

- [ ] **Advanced Scheduling** - Seasonal watering profiles
  - Spring: More frequent watering
  - Summer: Peak watering
  - Fall: Reduce watering
  - Winter: Minimal watering

- [ ] **Automatic Soil Type Detection** - Calibration wizard
  - Implementation: User runs calibration routine
  - System learns min/max moisture values
  - Adjusts thresholds automatically

---

## 🛠️ How to Add Features

### Adding a New API Endpoint

**Step 1: Define Pydantic Model** (if needed)

```python
# In src/main.py, after existing models

class MyNewDataModel(BaseModel):
    """
    Pydantic model for validating incoming data.
    
    All fields can have type hints + validation.
    """
    field1: str
    field2: Optional[int] = None
    
    # Custom validation
    @validator('field1')
    def field1_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Field1 cannot be empty')
        return v
```

**Step 2: Add Database Model** (if storing new data)

```python
# In src/main.py, in database models section

class MyNewTable(Base):
    __tablename__ = "my_new_table"
    
    id = Column(Integer, primary_key=True)
    bed_id = Column(String, index=True)
    value = Column(Float)
    timestamp = Column(DateTime)
```

**Step 3: Add Endpoint**

```python
@app.get("/api/my-new-endpoint/{bed_id}", tags=["Beds"])
def my_new_endpoint(
    bed_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Comprehensive docstring with:
    - Description of what endpoint does
    - Args/parameters explanation
    - Example response
    """
    # Query database
    results = db.query(MyNewTable).filter(
        MyNewTable.bed_id == bed_id
    ).limit(limit).all()
    
    # Return formatted response
    return [{
        "field": r.field,
        "timestamp": r.timestamp
    } for r in results]
```

**Step 4: Test**

1. Restart server: `uvicorn src.main:app --reload`
2. Visit `/docs` in browser
3. Try endpoint in Swagger UI
4. Test with curl:
   ```bash
   curl http://127.0.0.1:8000/api/my-new-endpoint/bed_1?limit=10
   ```

**Step 5: Document**

1. Add to API-SPEC.md with examples
2. Update README.md if user-facing
3. Add code comments if complex logic

---

### Adding a New Discord Command

**Step 1: Edit bot/bot.py**

```python
@bot.command()
async def mycommand(ctx):
    """Command docstring."""
    
    # Get data from API
    try:
        response = requests.get(f"{API_BASE}/api/endpoint")
        data = response.json()
    except:
        await ctx.send("❌ API error")
        return
    
    # Build embed
    embed = discord.Embed(
        title="My Command",
        description="Description here",
        color=0x2ecc71  # Green
    )
    
    embed.add_field(
        name="Field Name",
        value="Field value",
        inline=False
    )
    
    await ctx.send(embed=embed)
```

**Step 2: Test**

1. Restart bot: `python bot/bot.py`
2. In Discord: `.mycommand`
3. Check console for errors

---

### Modifying Watering Logic

**Location:** `src/main.py`, function `should_water()`

**Current Logic:**
1. Check if moisture < threshold
2. Check if rain is forecasted
3. Check if cooldown has expired
4. Return decision

**To Modify:**

```python
# Find the should_water endpoint
@app.post("/api/should-water")
def should_water(bed_id: str, average_moisture: float):
    # ... existing code ...
    
    # Add your logic here
    if some_condition:
        return {"water": True, "reason": "custom_reason"}
    
    # ... rest of logic ...
```

**Example: Add timezone support**

```python
from zoneinfo import ZoneInfo
import pytz

# Store timezone in bed_config
# Check if it's "watering hours" (e.g., 6am-8pm only)
# Refuse to water outside those hours
```

---

## 🧪 Testing Guide

### Manual Testing (Quick)

```bash
# Terminal 1: Start server
cd PlantWater-API-server
uvicorn src.main:app --reload

# Terminal 2: Run simulator
python src/simulator.py

# Terminal 3: Test endpoints
curl http://127.0.0.1:8000/api/beds/latest
curl http://127.0.0.1:8000/api/beds/bed_1/stats
```

### Automated Testing (Future)

```bash
# Create tests/test_endpoints.py
pytest tests/

# Coverage report
pytest --cov=src tests/
```

**Test Template:**

```python
import pytest
import requests

API_BASE = "http://127.0.0.1:8000"

def test_health_check():
    """Test that API is running."""
    response = requests.get(f"{API_BASE}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_bed_data_ingestion():
    """Test sensor data storage."""
    payload = {
        "bed_id": "test_bed",
        "timestamp": "2026-04-17T10:00:00Z",
        "sensors": [500.0, 505.0, 510.0, 515.0, 500.0],
        "average": 506.0,
        "valve_state": "OFF",
        "rssi": -50
    }
    
    response = requests.post(
        f"{API_BASE}/api/bed-data",
        json=payload,
        headers={"x-api-key": "test_key"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "stored"

def test_watering_decision():
    """Test watering decision logic."""
    response = requests.post(
        f"{API_BASE}/api/should-water",
        params={"bed_id": "bed_1", "average_moisture": 700}
    )
    
    assert response.status_code == 200
    assert "water" in response.json()
```

---

## 📊 Database Maintenance

### Backup Database

```bash
# Manual backup
cp database.db database.db.backup

# Automated daily backup (Linux/Mac cron)
0 2 * * * cp /path/to/database.db /backups/database.db.$(date +\%Y\%m\%d)

# For Windows Task Scheduler, create batch file:
# @echo off
# copy database.db database.db.%date:~-4,4%%date:~-10,2%%date:~-7,2%
```

### Clean Old Data

```bash
# Delete readings older than 7 days
DELETE FROM bed_readings WHERE timestamp < datetime('now', '-7 days');

# Get database size
SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();
```

### Optimize Database

```bash
# Vacuum/compact
VACUUM;

# Reindex
REINDEX;
```

---

## 🔧 Configuration Management

### Environment Variables (.env)

```bash
# Required
OPENWEATHER_API_KEY=xxxxxxxxxxxx

# Optional
DISCORD_TOKEN=xxxxxxxxxxxx
CITY=Detroit,US
DATABASE_URL=sqlite:///./database.db
API_KEY=your_super_secret_key
```

### Runtime Configuration (src/main.py)

Location of tunable parameters:

```python
# Weather
OPENWEATHER_API_KEY = "..."
CITY = "Detroit,US"

# Database
DATABASE_URL = "sqlite:///./database.db"

# API
API_KEY = "your_super_secret_key"

# Cache TTL
WEATHER_CACHE_MINUTES = 10
WEATHER_UPDATE_SECONDS = 60

# Default bed config
DEFAULT_MOISTURE_THRESHOLD = 600
DEFAULT_WATERING_DURATION_SEC = 3
DEFAULT_COOLDOWN_SEC = 30
DEFAULT_SAMPLING_INTERVAL_SEC = 10
```

---

## 🚀 Deployment Checklist

Before going to production:

- [ ] Set strong API_KEY in src/main.py
- [ ] Create .env file with real API keys
- [ ] Add .env to .gitignore
- [ ] Test with real ESP32 hardware
- [ ] Set up automated backups
- [ ] Enable HTTPS (use reverse proxy like nginx)
- [ ] Set up monitoring/alerts
- [ ] Document any customizations
- [ ] Test Discord bot with real Discord server
- [ ] Implement rate limiting
- [ ] Set up logging
- [ ] Security audit of inputs/outputs
- [ ] Load testing with simulator

---

## 🐛 Debugging Tips

### API Issues

```bash
# Check server logs
# Look for error messages in terminal where you ran uvicorn

# Test specific endpoint
curl -v http://127.0.0.1:8000/api/beds/latest

# Use Swagger UI at /docs for interactive testing
# Shows request/response bodies clearly
```

### Database Issues

```bash
# Open with DB Browser
# File → Open → database.db

# Or SQLite CLI
sqlite3 database.db
sqlite> SELECT COUNT(*) FROM bed_readings;
sqlite> SELECT * FROM bed_readings LIMIT 1;
```

### Discord Bot Issues

```bash
# Check token in .env
# Verify bot has permissions in Discord server
# Check console output for errors
# Enable debug logging: add to bot/bot.py
# discord.utils.setup_logging()
```

### Simulator Issues

```bash
# Check simulator output
python src/simulator.py

# Verify API is running on http://127.0.0.1:8000
# Check API key matches in simulator.py and main.py
```

---

## 📚 Code Organization

### src/main.py Structure

```
Imports
  ↓
Environment Setup
  ↓
Global Variables & State
  ↓
FastAPI App Initialization
  ↓
Database Models
  ↓
Pydantic Models
  ↓
Authentication Functions
  ↓
Helper Functions (weather, decision logic)
  ↓
API Endpoints (organized by tag)
  ↓
Background Threads
```

### Naming Conventions

- **Endpoints:** `/api/category/action` (e.g., `/api/beds/history`)
- **Functions:** `snake_case` (e.g., `get_bed_data()`)
- **Classes:** `PascalCase` (e.g., `BedReading`)
- **Constants:** `UPPER_CASE` (e.g., `API_KEY`)
- **Database tables:** `snake_case` (e.g., `bed_readings`)

---

## 🤝 Contributing Guidelines

### Code Style

- Use type hints: `def func(param: str) -> dict:`
- Comment complex logic
- Max line length: 100 characters
- Use docstrings for functions/classes

### Commit Message Format

```
[TAG] Short description

Longer explanation if needed.

Related to #issue_number
```

**Tags:**
- `[FEATURE]` - New functionality
- `[BUGFIX]` - Bug fix
- `[DOCS]` - Documentation
- `[REFACTOR]` - Code cleanup
- `[TEST]` - Tests

### PR Checklist

- [ ] Code tested locally
- [ ] Simulator still works
- [ ] API still responds at /docs
- [ ] New endpoints documented
- [ ] No hardcoded secrets
- [ ] No breaking changes (if possible)

---

## 🔐 Security Best Practices

### Input Validation

- Pydantic handles most validation automatically
- Always validate user inputs
- Use parameterized queries (SQLAlchemy does this)

### API Key Management

- Change default API_KEY before production
- Store in environment variables, not in code
- Implement key rotation
- Log API key usage for audit

### Database Security

- SQLite fine for dev, use PostgreSQL for production
- Enable connection encryption
- Regular backups
- Limit database file permissions (chmod 600)

### HTTPS/TLS

- Use reverse proxy (nginx, traefik) for HTTPS
- Get free certificate (Let's Encrypt)
- Redirect HTTP to HTTPS

---

## 🎓 Learning Resources

### FastAPI

- Official docs: https://fastapi.tiangolo.com
- Video tutorials: https://www.youtube.com/results?search_query=fastapi+tutorial

### SQLAlchemy

- Official docs: https://docs.sqlalchemy.org
- 2.0 tutorial: https://docs.sqlalchemy.org/en/20/tutorial/

### Discord.py

- Official docs: https://discordpy.readthedocs.io
- Bot examples: https://github.com/Rapptz/discord.py/tree/master/examples

### OpenWeather API

- Docs: https://openweathermap.org/api
- Free tier: One Meteorological Call API

### IoT/ESP32

- ESP32 official: https://www.espressif.com/
- Arduino IDE setup: https://docs.espressif.com/projects/arduino-esp32/

---

## 📞 Support & Questions

- **Documentation:** Check README.md + API-SPEC.md
- **Code Comments:** Read comments in src/main.py
- **API Testing:** Use /docs Swagger UI
- **Issues:** Create GitHub issue with details
- **Discord:** Join server for real-time help

---

## 🗓️ Release Roadmap

| Version | ETA | Features |
|---------|-----|----------|
| 1.0 | ✅ Done | Core API, Simulator, Discord |
| 1.1 | Q2 2026 | SMS alerts, API key management |
| 1.2 | Q3 2026 | Web dashboard redesign, export |
| 2.0 | Q4 2026 | Multi-location, mobile app, ML |

---

**Last Updated:** 2026-04-17  
**Maintainer:** PlantWater Project  
**Status:** Active Development 🚀

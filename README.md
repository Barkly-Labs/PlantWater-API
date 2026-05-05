# 🌱 PlantWater API Server

<p align="center">
  <img src="ezgif-4963a1d02fff645e.gif" width="700"/>
</p>

> **Smart Irrigation System** — Real-time soil moisture monitoring + weather-aware watering automation + Discord bot integration. Built with FastAPI, SQLite, and ESP32 sensor networks.

---

## 🎯 What is PlantWater?

PlantWater is a complete smart irrigation solution that:

- 📊 **Collects** real-time soil moisture data from plant beds via WiFi-enabled sensors
- 🤖 **Decides** when to water based on soil conditions + weather forecasts
- 💧 **Controls** irrigation valves automatically or via API
- 📈 **Tracks** lifetime watering stats, plant health, and system performance
- 🔌 **Integrates** with Discord for status updates + manual overrides
- 🌐 **Exposes** RESTful APIs for frontend dashboards, mobile apps, or custom automations

Perfect for hobby growers, smart gardens, agricultural monitoring, or anyone who wants to automate watering without overwatering plants.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenWeather API key (free tier available at https://openweathermap.org/api)
- Optional: Discord bot token (for Discord integration)

### Installation

```bash
# Clone the repo
git clone https://github.com/nickyblackburn/PlantWater-API-server.git
cd PlantWater-API-server

# Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic requests python-dotenv scikit-learn numpy

# Set up environment variables (create .env in repo root)
echo "OPENWEATHER_API_KEY=your_api_key_here" > .env
echo "DISCORD_TOKEN=your_bot_token_here" >> .env
```

### Start the Server

```bash
uvicorn src.main:app --reload
```

Server runs at `http://127.0.0.1:8000`

**Interactive API docs:** `http://127.0.0.1:8000/docs`

### Run the Simulator (Testing)

```bash
python src/simulator.py
```

This sends synthetic sensor data every 2 seconds + exercises watering logic. Perfect for development/testing.

### Run Discord Bot (Optional)

```bash
python bot/bot.py
```

Bot connects to Discord and responds to `.status` and `.help` commands.

---

## 📁 Repository Structure

```
PlantWater-API-server/
├── src/
│   ├── main.py              # FastAPI app + all endpoints + database models
│   └── simulator.py         # Test simulator for synthetic sensor data
├── bot/
│   └── bot.py               # Discord bot integration
├── database.db              # SQLite database (auto-created)
├── README.md                # Main documentation (this file)
├── API-SPEC.md              # Detailed API specification
├── startserver.bat          # Windows batch script to start server
└── .env                     # Configuration (create this)
```

---

## 🔌 API Overview

All endpoints are fully documented at `/docs` (Swagger UI) and `/redoc` (ReDoc).

### Core Concepts

- **Bed:** A physical plant bed with 5 soil moisture sensors
- **Reading:** A snapshot of sensor data + system state at a moment in time
- **Config:** Watering parameters for a bed (thresholds, timing, etc.)
- **Valve:** Irrigation control valve (ON/OFF)
- **Plant Health:** 0-100 score tracking plant wellness based on watering patterns

### Endpoint Categories

| Category | Purpose | Key Endpoints |
|----------|---------|---------------|
| **System** | Health checks, API info | `/health`, `/docs` |
| **Beds** | Sensor data, history, stats, graphs | `/api/beds/*`, `/api/beds/{bed_id}/graph`, `/api/beds/{bed_id}/history` |
| **Irrigation** | Watering decisions, valve control, lifetime stats | `/api/should-water`, `/api/beds/{bed_id}/lifetime` |
| **Weather** | Rain prediction, current conditions | `/api/will-rain`, `/api/weather/current` |
| **Config** | Bed settings, tuning | `/api/config/{bed_id}` |

---

## 📡 Key Endpoints (Quick Reference)

### 📥 Ingest Sensor Data

```http
POST /api/bed-data
Content-Type: application/json

{
  "bed_id": "bed_1",
  "timestamp": "2026-04-17T10:30:00Z",
  "sensors": [520.0, 505.0, 510.0, 515.0, 500.0],
  "average": 510.0,
  "valve_state": "OFF",
  "rssi": -50,
  "plant_health": 85.5
}
```

**Response:**
```json
{
  "status": "stored",
  "bed_id": "bed_1"
}
```

---

### 📊 Get All Beds (Latest)

```http
GET /api/beds/latest
```

Returns the most recent reading for each bed.

**Response:**
```json
{
  "bed_1": {
    "bed_id": "bed_1",
    "timestamp": "2026-04-17T10:30:00",
    "average": 510.0,
    "valve_state": "OFF",
    "rssi": -50,
    "sensors": [520.0, 505.0, 510.0, 515.0, 500.0]
  },
  "bed_2": { ... }
}
```

---

### 📈 Get Full Graph Data

```http
GET /api/beds/{bed_id}/full-graph?limit=200
```

Returns timestamps, moisture, valve state, RSSI, and plant health for charting.

**Response:**
```json
{
  "timestamps": ["2026-04-17T10:00:00", "2026-04-17T10:05:00", ...],
  "moisture": [520.0, 515.0, 510.0, ...],
  "valve": [0, 0, 1, 0, 0, ...],
  "rssi": [-50, -52, -48, ...],
  "plant_health": [85.5, 84.2, 83.8, ...]
}
```

---

### 🤖 Should We Water? (Decision Engine)

```http
POST /api/should-water?bed_id=bed_1&average_moisture=650
```

Evaluates if a bed should be watered. Considers soil moisture against threshold + weather forecast.

**Response:**
```json
{
  "water": true,
  "reason": "soil_dry",
  "moisture": 650,
  "threshold": 600,
  "will_rain": false
}
```

---

### ⚙️ Get/Set Bed Configuration

```http
GET /api/config/{bed_id}
```

**Response:**
```json
{
  "bed_id": "bed_1",
  "moisture_threshold": 600,
  "watering_duration_sec": 3,
  "cooldown_sec": 30,
  "sampling_interval_sec": 10
}
```

**Update configuration (POST):**
```http
POST /api/config/{bed_id}
Content-Type: application/json

{
  "moisture_threshold": 550,
  "watering_duration_sec": 5
}
```

---

### 💧 Lifetime Statistics

```http
GET /api/beds/{bed_id}/lifetime
```

Total watering events, duration, average moisture since system started.

**Response:**
```json
{
  "bed_id": "bed_1",
  "times_watered": 45,
  "last_watered": "2026-04-17T10:25:00",
  "total_watering_minutes": 156.5,
  "avg_moisture": 560.3
}
```

---

### 🌧️ Weather Endpoints

```http
GET /api/weather/current        # Current weather conditions
GET /api/will-rain              # Rain forecast (boolean + confidence)
```

---

### 🏥 Health Check

```http
GET /health
```

Returns `{"status": "ok"}` if API is running.

---

## 🎮 Simulator Behavior

`src/simulator.py` sends realistic test data every 2 seconds:

1. **Defines 4 simulated beds** (`bed_1` through `bed_4`)
2. **Simulates soil drying** with random fluctuations (-0.5 to -3 units per cycle)
3. **Generates 5 sensor readings** per bed (with ±5-15 unit noise for realism)
4. **Posts to `/api/bed-data`** — server stores in database
5. **Calls `/api/should-water`** — asks if watering should occur
6. **If YES:** simulates water boost (moisture increases 5-15 units)
7. **Tracks plant health** — improves with optimal watering, degrades from drought/overwatering
   - Drought stress (moisture > 750): -0.3 health/cycle
   - Overwatering stress (moisture < 300): -0.1 health/cycle
   - Optimal zone (300-750): +0.05 health/cycle
8. **Sends heartbeats** — periodic connectivity check to `/api/node/heartbeat`
9. **Repeats forever** until stopped (Ctrl+C)

Perfect for testing the full stack without real hardware.

---

## 🤝 Discord Bot Integration

Located in `bot/bot.py`. Start with:

```bash
python bot/bot.py
```

### Commands

```
.help        — Shows help + command list
.status      — Live bed status (moisture, valve state, signal strength, plant health)
```

### Status Output Example

```
🌱 Smart Garden Status
Live soil moisture readings

🌱 Bed 1 (bed_1)
Moisture: 510.0
State: 🌱 Healthy
Valve: 🔒 OFF
Signal: 🟢 strong

🌱 Bed 2 (bed_2)
Moisture: 650.0
State: 🏜️ Dry
Valve: 🚰 ON
Signal: 🟡 medium

🚰 Watering: Bed 2
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Required for weather integration
OPENWEATHER_API_KEY=e88c64c56baab21c5eeff4def1c026be

# Optional for Discord bot
DISCORD_TOKEN=your_discord_bot_token

# Optional (defaults shown)
CITY=Detroit,US
```

### Code Configuration (src/main.py)

| Setting | Default | Purpose |
|---------|---------|---------|
| `API_KEY` | `"your_super_secret_key"` | API authentication for ESP32 + simulator |
| `DATABASE_URL` | `"sqlite:///./database.db"` | SQLite database location |
| `CITY` | `"Detroit,US"` | Weather location |
| Weather cache TTL | 10 minutes | How long to cache weather data |
| Weather update loop | 60 seconds | Background thread update interval |

---

## 🗄️ Database Schema

### bed_readings
Stores historical sensor data from all beds.

| Column | Type | Notes |
|--------|------|-------|
| id | int | Primary key |
| bed_id | str | Indexed for fast queries |
| timestamp | datetime | When reading was captured (UTC) |
| average | float | Average moisture across 5 sensors |
| valve_state | str | "ON" or "OFF" |
| weather | json | Weather data at time of reading (nullable) |
| rssi | int | WiFi signal strength (dBm) |
| sensors | json | Array of 5 individual sensor values |
| plant_health | float | 0-100 plant wellness score (nullable) |

### bed_config
Per-bed watering settings.

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| id | int | — | Primary key |
| bed_id | str | — | Unique bed identifier |
| moisture_threshold | int | 600 | Below this value, watering triggered |
| watering_duration_sec | int | 3 | Seconds to run valve |
| cooldown_sec | int | 30 | Min seconds before next watering |
| sampling_interval_sec | int | 10 | Seconds between sensor reads |

### bed_meta
Metadata for display + device tracking.

| Column | Type | Purpose |
|--------|------|---------|
| id | int | Primary key |
| bed_id | str | Unique bed identifier |
| name | str | Display name (e.g., "Tomatoes") |
| icon | str | Emoji (e.g., "🍅") |
| ip | str | ESP32 device IP address |

---

## 🛠️ Development

### Adding a New Endpoint

1. Define Pydantic model(s) in `src/main.py`
2. Add `@app.get()` or `@app.post()` decorator
3. Include `tags=["Category"]` for API docs organization
4. Add comprehensive docstring with description + example
5. Test via `/docs` Swagger UI

### Running Tests

```bash
# Terminal 1: Start server
uvicorn src.main:app --reload

# Terminal 2: Run simulator
python src/simulator.py

# Browser: Check live data
# http://127.0.0.1:8000/docs
```

### Debugging

- **API Logs:** Terminal where server is running
- **Database:** Open `database.db` with [DB Browser for SQLite](https://sqlitebrowser.org)
- **Simulator Output:** Shows bed status every 2 seconds
- **Discord Bot:** Logs to console when commands invoked
- **API Docs:** `/docs` (Swagger) or `/redoc` (ReDoc)

---

## 🚨 Moisture Value Reference

Soil moisture readings range from **0 (dry)** to **1023 (saturated)** (typical ADC range).

| Range | State | Meaning |
|-------|-------|---------|
| 0-300 | 💧 Saturated | Overwatering risk |
| 300-500 | 🌱 Healthy | Optimal watering zone |
| 500-700 | 🌤️ Dry | Getting thirsty, water soon |
| 700+ | 🏜️ Very Dry | Needs immediate watering |

---

## 📈 Plant Health Score (0-100)

- **90-100:** Thriving, optimal watering
- **70-89:** Healthy, minor stress
- **50-69:** Moderate stress, adjust watering
- **20-49:** Severe stress, urgent action needed
- **0-19:** Critical, plant at risk

---

## 🗂️ TODO / Roadmap

- [ ] SMS alerts for critical plant health drops
- [ ] Machine learning plant health prediction (AI classification)
- [ ] IP address tracking for device management page
- [ ] Enhanced UX/UI for historical data page
- [ ] Plant health chart with 0-100% scale
- [ ] API key authentication on all sensitive endpoints
- [ ] Mobile app integration (React Native)
- [ ] Multi-location support (multiple servers)
- [ ] Export data to CSV/JSON
- [ ] Webhook notifications for external integrations

---

## 🔒 Security Best Practices

Before deploying to production:

- [ ] Set strong `API_KEY` in `src/main.py`
- [ ] Store secrets in `.env` file (never commit to Git)
- [ ] Add `.env` to `.gitignore`
- [ ] Use HTTPS if exposing API to internet
- [ ] Implement rate limiting on endpoints
- [ ] Consider PostgreSQL instead of SQLite for scale
- [ ] Enable CORS only for trusted domains
- [ ] Validate all input (Pydantic handles this)
- [ ] Regular database backups

---

## 🚀 Deployment

### Local (Development)
```bash
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### Production (example with Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app --bind 0.0.0.0:8000
```

### Docker (coming soon)
```bash
docker build -t plantwater-api .
docker run -p 8000:8000 plantwater-api
```

---

## 📚 Additional Documentation

- **[API-SPEC.md](./API-SPEC.md)** — Complete endpoint reference with examples
- **[src/main.py](./src/main.py)** — Code comments for implementation details
- **FastAPI Docs:** `/docs` (Swagger UI) or `/redoc` (ReDoc)

---

## 🤝 Contributing

Found a bug? Have a feature idea? PRs welcome!

Steps to contribute:
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

- Check `/docs` (Swagger) for live API reference
- Review code comments in `src/main.py` for implementation details
- Run simulator to test end-to-end flow
- Open an issue on GitHub for bugs/questions

---

## 📄 License

MIT License — feel free to fork, modify, and deploy!

---

**Built with 💚 for plant lovers + IoT enthusiasts**

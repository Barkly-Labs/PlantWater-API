# 🌱 PlantWater API Specification

Complete technical reference for all endpoints in the PlantWater Smart Irrigation System.

**Base URL:** `http://127.0.0.1:8000`  
**API Version:** 1.0  
**Authentication:** API Key (`x-api-key` header)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Data Models](#data-models)
3. [System Endpoints](#system-endpoints)
4. [Bed Data Endpoints](#bed-data-endpoints)
5. [Configuration Endpoints](#configuration-endpoints)
6. [Irrigation Control](#irrigation-control)
7. [Weather Endpoints](#weather-endpoints)
8. [Error Handling](#error-handling)
9. [Rate Limits](#rate-limits)
10. [Examples](#examples)

---

## Authentication

### API Key

Most endpoints require an API key passed via header:

```http
x-api-key: your_super_secret_key
```

**Current Default:** `"your_super_secret_key"` (change in `src/main.py` before production)

**Endpoints that require auth:**
- `POST /api/bed-data`
- `POST /api/config/{bed_id}`
- `POST /api/beds/{bed_id}/water-cycle`
- `POST /api/beds/{bed_id}/mode`

**Endpoints that are public:**
- `GET /api/beds`
- `GET /api/beds/latest`
- `GET /api/beds/{bed_id}/history`
- `GET /api/beds/{bed_id}/range`
- `GET /api/beds/{bed_id}/graph`
- `GET /api/beds/{bed_id}/full-graph`
- `GET /api/beds/{bed_id}/stats`
- `GET /api/beds/{bed_id}/lifetime`
- `GET /api/config/{bed_id}`
- `POST /api/should-water`
- `GET /api/weather/current`
- `GET /api/will-rain`
- `GET /health`

---

## Data Models

### BedData (Request Body)

Schema for sensor readings from ESP32 devices.

```json
{
  "bed_id": "string",                    // Unique bed identifier (required)
  "timestamp": "2026-04-17T10:30:00Z",   // ISO 8601 format (required)
  "sensors": [520.0, 505.0, ...],        // Array of 5 float values (required)
  "average": 510.0,                      // Average of sensors array (required)
  "valve_state": "OFF",                  // "ON" or "OFF" (required)
  "rssi": -50,                           // WiFi signal dBm (optional, -100 to -30)
  "plant_health": 85.5                   // 0-100 score (optional)
}
```

### BedConfig (Request Body)

Schema for updating bed configuration.

```json
{
  "moisture_threshold": 600,             // int, optional
  "watering_duration_sec": 3,            // int, optional
  "cooldown_sec": 30,                    // int, optional
  "sampling_interval_sec": 10            // int, optional
}
```

### BedReading (Response)

Stored sensor reading from database.

```json
{
  "id": 1234,
  "bed_id": "bed_1",
  "timestamp": "2026-04-17T10:30:00",
  "average": 510.0,
  "valve_state": "OFF",
  "weather": {...},                      // Nullable JSON
  "rssi": -50,
  "sensors": [520.0, 505.0, 510.0, 515.0, 500.0],
  "plant_health": 85.5
}
```

### BedConfig (Response)

Current configuration for a bed.

```json
{
  "bed_id": "bed_1",
  "moisture_threshold": 600,
  "watering_duration_sec": 3,
  "cooldown_sec": 30,
  "sampling_interval_sec": 10
}
```

---

## System Endpoints

### 🏥 Health Check

**Endpoint:** `GET /health`

**Description:** Simple health check to verify API is running.

**Response:** `200 OK`
```json
{
  "status": "ok"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/health
```

---

## Bed Data Endpoints

### 📥 Store Bed Reading

**Endpoint:** `POST /api/bed-data`

**Authentication:** Required (API key)

**Description:** Stores incoming sensor reading from ESP32 device.

**Request Body:**
```json
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

**Response:** `200 OK`
```json
{
  "status": "stored",
  "bed_id": "bed_1"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid JSON or missing required fields
- `401 Unauthorized` - Invalid or missing API key

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/bed-data \
  -H "x-api-key: your_super_secret_key" \
  -H "Content-Type: application/json" \
  -d '{
    "bed_id": "bed_1",
    "timestamp": "2026-04-17T10:30:00Z",
    "sensors": [520.0, 505.0, 510.0, 515.0, 500.0],
    "average": 510.0,
    "valve_state": "OFF",
    "rssi": -50
  }'
```

---

### 📊 Get Latest Readings (All Beds)

**Endpoint:** `GET /api/beds/latest`

**Description:** Returns the most recent reading for each bed.

**Query Parameters:** None

**Response:** `200 OK`
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
  "bed_2": {
    "bed_id": "bed_2",
    "timestamp": "2026-04-17T10:29:55",
    "average": 620.0,
    "valve_state": "ON",
    "rssi": -55,
    "sensors": [625.0, 615.0, 620.0, 630.0, 615.0]
  }
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/beds/latest
```

---

### 📈 Get Bed History

**Endpoint:** `GET /api/beds/{bed_id}/history`

**Description:** Retrieve last 100 readings for a specific bed.

**Path Parameters:**
- `bed_id` (string, required) - Bed identifier (e.g., "bed_1")

**Query Parameters:**
- None

**Response:** `200 OK`
```json
[
  {
    "timestamp": "2026-04-17T10:30:00",
    "average": 510.0,
    "valve_state": "OFF",
    "sensors": [520.0, 505.0, 510.0, 515.0, 500.0]
  },
  {
    "timestamp": "2026-04-17T10:29:55",
    "average": 515.0,
    "valve_state": "OFF",
    "sensors": [520.0, 510.0, 515.0, 520.0, 505.0]
  }
]
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/beds/bed_1/history
```

---

### 📅 Get Time Range Data

**Endpoint:** `GET /api/beds/{bed_id}/range`

**Description:** Query readings within a specific time range.

**Path Parameters:**
- `bed_id` (string, required) - Bed identifier

**Query Parameters:**
- `start` (ISO 8601 datetime, required) - Start of range (inclusive)
- `end` (ISO 8601 datetime, required) - End of range (inclusive)

**Response:** `200 OK`
```json
[
  {
    "timestamp": "2026-04-16T14:00:00",
    "average": 450.0,
    "valve_state": "OFF"
  },
  {
    "timestamp": "2026-04-16T14:05:00",
    "average": 480.0,
    "valve_state": "ON"
  }
]
```

**Example:**
```bash
curl "http://127.0.0.1:8000/api/beds/bed_1/range?start=2026-04-16T00:00:00&end=2026-04-17T23:59:59"
```

---

### 📊 Get Graph Data (Simple)

**Endpoint:** `GET /api/beds/{bed_id}/graph`

**Description:** Get chart-ready data (3 arrays: timestamps, moisture, valve).

**Path Parameters:**
- `bed_id` (string, required)

**Query Parameters:**
- `limit` (int, optional, default=200) - Max readings to return

**Response:** `200 OK`
```json
{
  "timestamps": [
    "2026-04-17T10:00:00",
    "2026-04-17T10:05:00",
    "2026-04-17T10:10:00"
  ],
  "average": [500.0, 510.0, 520.0],
  "valve": ["OFF", "OFF", "ON"]
}
```

**Example:**
```bash
curl "http://127.0.0.1:8000/api/beds/bed_1/graph?limit=100"
```

---

### 📊 Get Full Graph Data

**Endpoint:** `GET /api/beds/{bed_id}/full-graph`

**Description:** Get comprehensive chart data including RSSI and plant health.

**Path Parameters:**
- `bed_id` (string, required)

**Query Parameters:**
- `limit` (int, optional, default=200) - Max readings to return

**Response:** `200 OK`
```json
{
  "timestamps": ["2026-04-17T10:00:00", "2026-04-17T10:05:00"],
  "moisture": [500.0, 510.0],
  "rain": [0, 0],
  "valve": [0, 1],
  "rssi": [-50, -52],
  "plant_health": [85.5, 84.2]
}
```

**Note:** Valve is binary (0=OFF, 1=ON) in full-graph endpoint.

**Example:**
```bash
curl "http://127.0.0.1:8000/api/beds/bed_1/full-graph?limit=50"
```

---

### 📈 Get Statistics

**Endpoint:** `GET /api/beds/{bed_id}/stats`

**Description:** Aggregated statistics for all readings of a bed.

**Path Parameters:**
- `bed_id` (string, required)

**Response:** `200 OK`
```json
{
  "count": 1250,
  "min": 350.0,
  "max": 980.0,
  "avg": 560.5,
  "last": 510.0
}
```

| Field | Meaning |
|-------|---------|
| count | Total number of readings |
| min | Lowest moisture ever recorded |
| max | Highest moisture ever recorded |
| avg | Average across all readings |
| last | Most recent moisture value |

**Example:**
```bash
curl http://127.0.0.1:8000/api/beds/bed_1/stats
```

---

### 💧 Get Lifetime Statistics

**Endpoint:** `GET /api/beds/{bed_id}/lifetime`

**Description:** Lifetime watering stats and performance metrics.

**Path Parameters:**
- `bed_id` (string, required)

**Response:** `200 OK`
```json
{
  "bed_id": "bed_1",
  "times_watered": 45,
  "last_watered": "2026-04-17T10:25:00",
  "total_watering_minutes": 156.5,
  "avg_moisture": 560.3
}
```

| Field | Meaning |
|-------|---------|
| bed_id | Bed identifier |
| times_watered | Total number of watering cycles |
| last_watered | Timestamp of most recent watering |
| total_watering_minutes | Cumulative valve open time (minutes) |
| avg_moisture | Average soil moisture across history |

**Example:**
```bash
curl http://127.0.0.1:8000/api/beds/bed_1/lifetime
```

---

## Configuration Endpoints

### ⚙️ Get Bed Configuration

**Endpoint:** `GET /api/config/{bed_id}`

**Description:** Retrieve current watering configuration for a bed.

**Path Parameters:**
- `bed_id` (string, required)

**Response:** `200 OK`
```json
{
  "bed_id": "bed_1",
  "moisture_threshold": 600,
  "watering_duration_sec": 3,
  "cooldown_sec": 30,
  "sampling_interval_sec": 10
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/config/bed_1
```

---

### ⚙️ Update Bed Configuration

**Endpoint:** `POST /api/config/{bed_id}`

**Authentication:** Required (API key)

**Description:** Update watering parameters for a bed. Supports partial updates.

**Path Parameters:**
- `bed_id` (string, required)

**Request Body:** (all fields optional)
```json
{
  "moisture_threshold": 550,
  "watering_duration_sec": 5,
  "cooldown_sec": 45,
  "sampling_interval_sec": 15
}
```

**Response:** `200 OK`
```json
{
  "bed_id": "bed_1",
  "moisture_threshold": 550,
  "watering_duration_sec": 5,
  "cooldown_sec": 45,
  "sampling_interval_sec": 15
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/config/bed_1 \
  -H "x-api-key: your_super_secret_key" \
  -H "Content-Type: application/json" \
  -d '{
    "moisture_threshold": 550,
    "watering_duration_sec": 5
  }'
```

---

## Irrigation Control

### 🤖 Watering Decision Engine

**Endpoint:** `POST /api/should-water`

**Description:** Evaluate if a bed should be watered now. Considers:
- Soil moisture vs. threshold
- Weather forecast (won't water if rain predicted)
- Cooldown period from last watering

**Query Parameters:**
- `bed_id` (string, required) - Bed identifier
- `average_moisture` (float, required) - Current soil moisture reading

**Response:** `200 OK`
```json
{
  "water": true,
  "reason": "soil_dry",
  "moisture": 650,
  "threshold": 600,
  "will_rain": false
}
```

| Field | Meaning |
|-------|---------|
| water | Boolean decision: should water now |
| reason | Why decision was made (e.g., "soil_dry", "cooldown", "rain_coming") |
| moisture | Current soil moisture value |
| threshold | Configured threshold for this bed |
| will_rain | Whether rain is forecasted |

**Example:**
```bash
curl -X POST "http://127.0.0.1:8000/api/should-water?bed_id=bed_1&average_moisture=650"
```

---

### 🚰 Valve Status

**Endpoint:** `GET /api/beds/{bed_id}/valve`

**Description:** Get current valve state for a bed.

**Path Parameters:**
- `bed_id` (string, required)

**Response:** `200 OK`
```json
{
  "bed_id": "bed_1",
  "valve_state": "ON"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/beds/bed_1/valve
```

---

### 💧 Water Cycle Control

**Endpoint:** `POST /api/beds/{bed_id}/water-cycle`

**Authentication:** Required (API key)

**Description:** Record start/stop of watering cycle for lifetime tracking.

**Path Parameters:**
- `bed_id` (string, required)

**Query Parameters:**
- `valve_state` (string, required) - "ON" to start, "OFF" to stop

**Response:** `200 OK`
```json
{
  "bed_id": "bed_1",
  "state": "started"
}
```

Or when stopping:
```json
{
  "bed_id": "bed_1",
  "state": "stopped",
  "duration_sec": 45
}
```

**Example:**
```bash
# Start watering
curl -X POST "http://127.0.0.1:8000/api/beds/bed_1/water-cycle?valve_state=ON" \
  -H "x-api-key: your_super_secret_key"

# Stop watering
curl -X POST "http://127.0.0.1:8000/api/beds/bed_1/water-cycle?valve_state=OFF" \
  -H "x-api-key: your_super_secret_key"
```

---

### 🎮 Bed Mode

**Endpoint:** `GET /api/beds/{bed_id}/mode`  
**Endpoint:** `POST /api/beds/{bed_id}/mode`

**Description:** Get or set operational mode for a bed (e.g., "normal", "manual").

**GET Response:**
```json
{
  "bed_id": "bed_1",
  "mode": "normal"
}
```

**POST Request:**
```json
{
  "mode": "manual"
}
```

**POST Response:**
```json
{
  "bed_id": "bed_1",
  "mode": "manual"
}
```

---

## Weather Endpoints

### 🌧️ Current Weather

**Endpoint:** `GET /api/weather/current`

**Description:** Get current weather conditions from OpenWeather API.

**Response:** `200 OK`
```json
{
  "temp": 72.5,
  "humidity": 65,
  "condition": "Partly Cloudy",
  "wind_speed": 8.5,
  "city": "Detroit,US",
  "timestamp": "2026-04-17T10:30:00"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/weather/current
```

---

### 🌧️ Rain Forecast

**Endpoint:** `GET /api/will-rain`

**Description:** Get cached rain forecast. Returns boolean based on 24-hour forecast.

**Response:** `200 OK`
```json
{
  "will_rain": false,
  "confidence": 0.15,
  "next_rain_hour": null
}
```

| Field | Meaning |
|-------|---------|
| will_rain | Boolean: is rain forecasted in next 24h |
| confidence | Confidence score (0.0-1.0) |
| next_rain_hour | Hours until rain (null if no rain) |

**Example:**
```bash
curl http://127.0.0.1:8000/api/will-rain
```

---

## Error Handling

### Error Response Format

All errors return appropriate HTTP status codes with JSON body:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid JSON, missing required field |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Requested bed doesn't exist |
| 500 | Server Error | Unexpected internal error |

### Example Error Response

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/bed-data \
  -H "x-api-key: wrong_key" \
  -H "Content-Type: application/json" \
  -d '{"bed_id": "bed_1"}'
```

**Response:** `401 Unauthorized`
```json
{
  "detail": "Invalid API key"
}
```

---

## Rate Limits

Currently no rate limits implemented. Future versions will include:
- Per-IP request limits
- Per-API-key request limits
- Time-window based throttling

---

## Examples

### Complete Flow: ESP32 → API → Decision

```bash
# 1. ESP32 sends sensor reading
curl -X POST http://127.0.0.1:8000/api/bed-data \
  -H "x-api-key: your_super_secret_key" \
  -H "Content-Type: application/json" \
  -d '{
    "bed_id": "bed_1",
    "timestamp": "2026-04-17T10:30:00Z",
    "sensors": [520.0, 505.0, 510.0, 515.0, 500.0],
    "average": 510.0,
    "valve_state": "OFF",
    "rssi": -50,
    "plant_health": 85.5
  }'

# Response: {"status": "stored", "bed_id": "bed_1"}

# 2. Query watering decision
curl -X POST "http://127.0.0.1:8000/api/should-water?bed_id=bed_1&average_moisture=510"

# Response: {"water": false, "reason": "above_threshold", ...}

# 3. If water=false, check why and get current config
curl http://127.0.0.1:8000/api/config/bed_1

# Response: {"bed_id": "bed_1", "moisture_threshold": 600, ...}

# 4. Moisture is 510, threshold is 600, so no watering needed
# Check the graph to visualize recent history
curl "http://127.0.0.1:8000/api/beds/bed_1/graph?limit=50"
```

---

### Dashboard Integration Example

```javascript
// Fetch all beds' latest data for dashboard display
async function updateDashboard() {
  const res = await fetch('http://127.0.0.1:8000/api/beds/latest');
  const beds = await res.json();

  Object.entries(beds).forEach(([bedId, data]) => {
    console.log(`${bedId}: ${data.average} moisture`);
    console.log(`  Valve: ${data.valve_state}`);
    console.log(`  Signal: ${data.rssi} dBm`);
  });
}

// Fetch graph data for charting
async function drawChart(bedId) {
  const res = await fetch(`http://127.0.0.1:8000/api/beds/${bedId}/full-graph?limit=200`);
  const data = await res.json();

  // Use with Chart.js, Plotly, etc.
  console.log('Timestamps:', data.timestamps);
  console.log('Moisture:', data.moisture);
  console.log('Valve:', data.valve);
  console.log('Plant Health:', data.plant_health);
}
```

---

## OpenAPI / Swagger

Full interactive API documentation available at:

- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`
- **OpenAPI JSON:** `http://127.0.0.1:8000/openapi.json`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-17 | Initial release |

---

**Last Updated:** 2026-04-17  
**Maintainer:** PlantWater Project  
**GitHub:** https://github.com/nickyblackburn/PlantWater-API-server

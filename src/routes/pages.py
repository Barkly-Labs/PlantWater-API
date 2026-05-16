"""
HTML Page Routes
Dashboard, devices, analytics, login, setup pages
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from db import get_db
from models import User, BedMetaDB
from auth import get_current_user

router = APIRouter()
























































GLOBAL_CSS = """
body {
    background:#0f1115;
    color:#ffffff;
    font-family: system-ui;
}

/* Global text rules */
p, span, div, h1, h2, h3, h4, h5, li {
    color:#ffffff;
}

/* Muted / secondary text */
.small,
.text-muted {
    color: rgba(255,255,255,0.65) !important;
}

/* Links */
a {
    color:#00ff9a;
}
a:hover {
    color:#00c77a;
}

/* Cards */
.card {
    background:#1b1f2a;
    border:1px solid #2a2f3a;
    color:#ffffff;
}

/* Navbar */
.navbar {
    background:#000;
    border-bottom:1px solid #2a2f3a;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px;
    align-items: stretch;
}

.node-card {
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

/* Status colors */
.status-good { color:#00ff9a; font-weight:bold; }
.status-warn { color:#ffcc00; font-weight:bold; }
.status-bad  { color:#ff4d4d; font-weight:bold; }

/* Utility */
.grid {
    display:grid;
    gap:10px;
}

body {
            background: radial-gradient(circle at top, #151922, #0f1115);
            color: #e6eaf2;
            font-family: system-ui, sans-serif;
        }

        .card {
            background: linear-gradient(145deg, #1b1f2a, #141821);
            border: 1px solid #2a2f3a;
            border-radius: 18px;
            margin-bottom: 14px;
        }

        .chart-wrap {
            position: relative;
            height: 320px;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
        }

        .stat {
            background: #12151c;
            padding: 12px;
            border-radius: 12px;
            text-align: center;
        }

        .weather-main {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .temp {
            font-size: 42px;
            font-weight: bold;
        }

"""


NAVBAR = """
<nav class="navbar navbar-expand-lg navbar-dark">
  <div class="container-fluid">

    <a class="navbar-brand" href="/">🌱 Smart Garden</a>

    <div class="navbar-nav">
      <a class="nav-link" href="/">Dashboard</a>
      <a class="nav-link" href="/nodes">🌿 Devices</a>
      <a class="nav-link" href="/notifications">📱 Notifications</a>
      <a class="nav-link" href="/api-keys">🔐 API Keys</a>
      <a class="nav-link" href="/app/docs">API Docs</a>
      <a class="nav-link" href="/about">About</a>
      <a class="nav-link" href="/logout">Logout</a>

    </div>

  </div>
</nav>
"""

def page(title: str, body: str):
    return f"""
<!DOCTYPE html>
<html>
<head>
<title>{title}</title>


<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js"></script>

<style>
{GLOBAL_CSS}
</style>

</head>

<body>

{NAVBAR}

{body}
<footer style="text-align:center; padding:20px; color:#9aa4b2; border-top:1px solid #2a2f3a; margin-top:40px;">
    Made with 💖 Nicky Blackburn
</footer>
</body>
</html>
"""


#################################
# main entry point for running the API server
###################################
@router.get("/", response_class=HTMLResponse, tags=["System"])
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)   # ✅ MUST BE HERE
):

    if not user:
        return RedirectResponse("/login")
    body =  """

<body>

<style>
/* 🔥 ADD ONLY: highlight style */
.selected-bed {
    border: 2px solid #4ade80 !important;
    box-shadow: 0 0 12px rgba(74, 222, 128, 0.5);
    transform: scale(1.01);
    transition: 0.15s ease;
}
</style>

<div class="container py-4">

<h2 class="mb-3">🌿 Garden Control Panel</h2>

<div id="weather" class="alert alert-info">Loading weather...</div>

<div class="row" id="beds"></div>

</div>



<script>

let bedMeta = {};
let selectedBed = null;

/* -------------------------
   META
------------------------- */
async function loadMeta() {
    try {
        const res = await fetch("/api/beds/meta");
        bedMeta = await res.json();
    } catch (e) {
        bedMeta = {};
    }
}

/* -------------------------
   WEATHER (FIXED)
------------------------- */
async function loadWeather() {
    try {
        const res = await fetch('/api/weather');
        const data = await res.json();

        document.getElementById("weather").innerText =
            data.is_raining_now
                ? "🌧 Currently raining"
                : data.will_rain
                    ? "🌧 Rain expected soon"
                    : "☀ Stable conditions";

    } catch (e) {
        document.getElementById("weather").innerText =
            "⚠ Weather unavailable";
    }
}

/* -------------------------
   STATUS
------------------------- */
function getStatus(avg) {
    if (avg > 700) return { text:"DRY", cls:"status-bad" };
    if (avg < 300) return { text:"WET", cls:"status-warn" };
    return { text:"HEALTHY", cls:"status-good" };
}

/* -------------------------
   NAV
------------------------- */
function goToBed(bedId) {
    window.location.href = `/bed/${bedId}/analytics`;
}

/* -------------------------
   ✨ NEW: highlight selection
------------------------- */
function selectBed(bedId) {
    selectedBed = bedId;

    document.querySelectorAll(".clickable-card").forEach(el => {
        el.classList.remove("selected-bed");
    });

    const el = document.getElementById(`bed-${bedId}`);
    if (el) el.classList.add("selected-bed");
}

/* -------------------------
   EDIT BED
------------------------- */
async function editBed(bedId) {
    const current = bedMeta[bedId] || {};

    const name = prompt("Plant / Bed Name:", current.name || bedId);
    if (name === null) return;

    const icon = prompt("Emoji / Icon:", current.icon || "🌱");
    if (icon === null) return;

    await fetch(`/api/beds/${bedId}/meta`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ name, icon })
    });

    await loadMeta();
    await loadBeds();
}

/* -------------------------
   LOAD BEDS
------------------------- */
async function loadBeds() {
    try {
        const latest = await fetch('/api/beds/latest').then(r => r.json());

        let html = "";

        for (const bed in latest) {

            const b = latest[bed];

            let life = {};
            try {
                life = await fetch(`/api/beds/${bed}/lifetime`).then(r => r.json());
            } catch (e) {
                life = { times_watered: 0, total_watering_minutes: 0 };
            }

            const status = getStatus(b.average);

            const meta = bedMeta[b.bed_id] || {};
            const name = meta.name || b.bed_id;
            const icon = meta.icon || "🌱";

            html += `
            <div class="col-md-4 mb-3">

                <div id="bed-${b.bed_id}"
                     class="card p-3 clickable-card"
                     onclick="selectBed('${b.bed_id}'); goToBed('${b.bed_id}')">

                    <h5>${icon} ${name}</h5>

                    <div class="small">ID: ${b.bed_id}</div>

                    <button class="btn btn-sm btn-outline-light mt-2"
                            onclick="event.stopPropagation(); editBed('${b.bed_id}')">
                        ✏ Edit
                    </button>

                    <p class="${status.cls} mt-2">${status.text}</p>

                    <p>💧 Moisture: ${b.average.toFixed(1)}</p>
                    <p>🚰 Valve: ${b.valve_state}</p>

                    <hr>

                    <p>🌊 Water Cycles: <b>${life.times_watered || 0}</b></p>
                    <p>⏱ Total Watering: <b>${life.total_watering_minutes || 0} min</b></p>

                </div>
            </div>
            `;
        }

        document.getElementById("beds").innerHTML = html;

    } catch (e) {
        document.getElementById("beds").innerHTML =
            "<p>⚠ Failed to load beds</p>";
    }
}

/* -------------------------
   INIT
------------------------- */
(async function init() {
    await loadMeta();
    await loadBeds();
    await loadWeather();

    setInterval(loadBeds, 3000);
    setInterval(loadWeather, 10000);
})();

</script>

</body>
</html>
"""
    return page("Dashboard", body)

# =======================================================
# 📖 ABOUT PAGE
# ============================================================


@router.get("/about", response_class=HTMLResponse, tags=["System"])
def about_page():
    body = """

<body>

<div class="container py-5">

    <div class="hero">
        <h1 class="glow">🌱 Smart Garden System</h1>
        <p style="color: #ffffff;">IoT irrigation system with weather-aware automation</p>
    </div>

    <!-- ABOUT -->
    <div class="card p-4 mb-4">
        <h4>📌 Project Overview</h4>
        <p>
            This system is a smart irrigation network using FastAPI,
            Bed Modules (esp32 controlled Auto watering systems), and a real-time dashboard.
            It models how an ESP32-based garden would monitor soil moisture
            and automatically control watering based on environmental conditions.
        </p>
    </div>

    <!-- TECH STACK -->
    <div class="card p-4 mb-4">
        <h4>⚙️ Tech Stack</h4>

        <span class="tag">FastAPI</span>
        <span class="tag">SQLite</span>
        <span class="tag">SQLAlchemy</span>
        <span class="tag">Chart.js</span>
        <span class="tag">Bootstrap</span>
        <span class="tag">Bed Modules (ESP32) based</span>
        <span class="tag">OpenWeather API</span>
    </div>

    <!-- FEATURES -->
    <div class="card p-4 mb-4">
        <h4>🌿 Features</h4>

        <ul>
            <li>Real-time soil moisture monitoring</li>
            <li>Automatic watering decision engine</li>
            <li>Weather-aware irrigation logic</li>
            <li>Historical sensor data storage</li>
            <li>Graph-based moisture tracking</li>
            <li>Configurable watering thresholds</li>
        </ul>
    </div>

    <!-- CREATOR -->
    <div class="card p-4 mb-4">
        <h4>👤 Creator</h4>

        <p>
            Built by <b>Nicky Blackburn</b><br>
            A personal IoT + backend systems project exploring automation,
            sensors, and real-time data systems.
        </p>

        <p class="text-muted">
            Version: 1.0 · Prototype System
        </p>
    </div>

    <!-- SYSTEM ARCHITECTURE -->
    <div class="card p-4 mb-4">
        <h4>🧠 System Flow</h4>

        <pre style="color:#9aa4b2;">
ESP32 Bed Modules (soil moisture & control valves)
    ↓
FastAPI Server
    ↓
SQLite Database
    ↓
Decision Engine (watering logic)
    ↓
Dashboard UI (Chart.js)
        </pre>
    </div>

    <!-- NAV -->
    <div class="text-center mt-4">
        <a href="/" class="btn btn-outline-light">← Back to Dashboard</a>
    </div>

</div>

</body>
</html>
"""
    return page("About", body)

###################################################
## 🌿 DEVICES PAGE - REAL-TIME NODE STATUSES
####################################################

from fastapi.responses import HTMLResponse

from fastapi import Depends
from fastapi.responses import HTMLResponse, RedirectResponse

@router.get("/nodes", response_class=HTMLResponse, tags=["System"])
def node_status_page(user: User = Depends(get_current_user)):

    if not user:
        return RedirectResponse("/login")

    body = """
<div class="container py-4">

<h2 class="mb-3">🛰 Garden Node Status</h2>

<div id="nodes" class="grid"></div>



</div>

<script>

let meta = {};

/* -------------------------
   META
------------------------- */
async function loadMeta() {
    const res = await fetch("/api/beds/meta");
    meta = await res.json();
}

/* -------------------------
   NODES
------------------------- */
async function loadNodes() {

    const res = await fetch("/api/beds/latest");
    const data = await res.json();

    let html = "";

    for (const bedId in data) {

        const n = data[bedId];
        const m = meta[bedId] || {};

        const name = m.name || bedId;
        const icon = m.icon || "🌱";

        let rssiClass = "good";
        if ((n.rssi ?? -100) < -70) rssiClass = "warn";
        if ((n.rssi ?? -100) < -85) rssiClass = "bad";

        html += `
<a class="node-link" href="/device/${bedId}">
    <div class="card node-card p-3">

        <h5>${icon} ${name}</h5>

        <div class="small">ID: ${bedId}</div>
        <div class="small">IP: ${n.ip ?? "unknown"}</div>

        <p class="${rssiClass}">
            📡 RSSI: ${n.rssi ?? "?"} dBm
        </p>

        <p>🔋 Battery: ${n.battery ? n.battery.toFixed(2) + "V" : "N/A"}</p>
        <p>💧 Moisture: ${n.average?.toFixed(1) ?? "?"}</p>
        <p>🚰 Valve: ${n.valve_state ?? "?"}</p>

    </div>
</a>
`;
    }

    document.getElementById("nodes").innerHTML = html;
}

/* -------------------------
   INIT
------------------------- */
(async function init() {
    await loadMeta();
    await loadNodes();

    setInterval(loadNodes, 3000);
})();

</script>

</body>
</html>
"""
    return page("Devices", body)

from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from fastapi import Depends
@router.get("/bed/{bed_id}/analytics", response_class=HTMLResponse, tags=["System"])
def bed_analytics_page(bed_id: str, db: Session = Depends(get_db)):

    meta = db.query(BedMetaDB).filter(BedMetaDB.bed_id == bed_id).first()

    bed_name = meta.name if meta and meta.name else bed_id
    bed_icon = meta.icon if meta and meta.icon else "🌱"
    title = f"{bed_icon} {bed_name} Analytics"

    html = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
body {
    background:#0f1115;
    color:#ffffff;
    font-family: system-ui;
}

p, span, div, h1, h2, h3, h4, h5, li {
    color:#ffffff;
}

.text-muted {
    color: rgba(255,255,255,0.65) !important;
}

a { color:#00ff9a; }
a:hover { color:#00c77a; }

.card {
    background:#1b1f2a;
    border:1px solid #2a2f3a;
    color:#ffffff;
}

.navbar {
    background:#000;
    border-bottom:1px solid #2a2f3a;
}

body {
    background: radial-gradient(circle at top, #151922, #0f1115);
    color: #e6eaf2;
    font-family: system-ui, sans-serif;
}

.card {
    background: linear-gradient(145deg, #1b1f2a, #141821);
    border: 1px solid #2a2f3a;
    border-radius: 18px;
    margin-bottom: 14px;
}

.chart-wrap {
    position: relative;
    height: 320px;
    width: 100%;
}

canvas {
    width: 100% !important;
    height: 100% !important;
}

.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
}

.stat {
    background: #12151c;
    padding: 12px;
    border-radius: 12px;
    text-align: center;
}

.weather-main {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.temp {
    font-size: 42px;
    font-weight: bold;
}

.status-good { color:#00ff9a; font-weight:bold; }
.status-warn { color:#ffcc00; font-weight:bold; }
.status-bad  { color:#ff4d4d; font-weight:bold; }

    </style>
</head>

<body>

<nav class="navbar navbar-expand-lg navbar-dark bg-black border-bottom border-secondary">
  <div class="container-fluid">

    <a class="navbar-brand" href="/">🌱 Smart Garden</a>

    <div class="navbar-nav">
      <a class="nav-link" href="/">Dashboard</a>
      <a class="nav-link" href="/nodes">🌿 Devices</a>
        <a class="nav-link" href="/notifications">📱 Notifications</a>
        <a class="nav-link" href="/api-keys">🔐 API Keys</a>
      <a class="nav-link" href="/app/docs">API Docs</a>
      <a class="nav-link" href="/about">About</a>
      <a class="nav-link" href="/logout">Logout</a>
    </div>

  </div>
</nav>

<div class="container py-4">

<h2>{title}</h2>

<div class="card p-3" id="summary">Loading...</div>

<div class="card p-3">
    <h5>🌤 Weather</h5>
    <div id="weatherBox">Loading weather...</div>
</div>

<div class="card p-3">
    <h5>💧 Moisture</h5>
    <div class="chart-wrap">
        <canvas id="moistureChart"></canvas>
    </div>
</div>

<div class="card p-3">
    <h5>🌱 Plant Health</h5>
    <div class="chart-wrap">
        <canvas id="healthChart"></canvas>
    </div>
</div>



</div>

<script>

let moistureChart;
let healthChart;

function toF(c) {
    return Math.round((c * 9/5) + 32);
}

async function loadAnalytics() {

    const res = await fetch("/api/beds/{bed_id}/full-graph");
    const data = await res.json();

    const life = await fetch("/api/beds/{bed_id}/lifetime").then(r => r.json());
    const weather = await fetch("/api/weather").then(r => r.json());
    const health = await fetch("/api/beds/{bed_id}/health").then(r => r.json());

    const timestamps = data.timestamps || [];
    const moisture = data.moisture || [];
    const plantHealth = data.plant_health || [];

    const minLen = Math.min(timestamps.length, moisture.length);

    const labels = timestamps.slice(0, minLen).map(t =>
        new Date(t).toLocaleTimeString()
    );

    const safeMoisture = moisture.slice(0, minLen);
    const safeHealth = plantHealth.slice(0, minLen);

    const avgMoisture = safeMoisture.length
        ? (safeMoisture.reduce((a,b)=>a+b,0)/safeMoisture.length).toFixed(1)
        : "0";

    // -----------------------------
    // FIX: strict status normalization (prevents "stress" leaks)
    // -----------------------------
    let status = health?.status ?? "unknown";

    const allowedStatuses = ["healthy", "warning", "bad"];

    if (!allowedStatuses.includes(status)) {
        status = "unknown";
    }

    const statusClass =
        status === "healthy" ? "status-good" :
        status === "warning" ? "status-warn" :
        status === "bad" ? "status-bad" :
        "";

    document.getElementById("summary").innerHTML =
        "<div class='stat-grid'>" +
        "<div class='stat'>💧 <b>" + avgMoisture + "</b> Avg</div>" +
        "<div class='stat'>🚰 <b>" + (life.times_watered || 0) + "</b> Watered</div>" +
        "<div class='stat'>⏱ <b>" + (life.total_watering_minutes || 0) + "m</b></div>" +
        "<div class='stat'>🌱 <b class='" + statusClass + "'>" + status + "</b></div>" +
        "</div>";

    moistureChart = new Chart(
        document.getElementById("moistureChart"),
        {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Moisture",
                    data: safeMoisture,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        }
    );

    healthChart = new Chart(
        document.getElementById("healthChart"),
        {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Plant Health",
                    data: safeHealth,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    borderColor: "#00ff9a",
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { min: 0, max: 100 }
                }
            }
        }
    );

    document.getElementById("weatherBox").innerHTML = `
        <div class="weather-main">
            <div>
                <div class="temp">
                    ${weather.temp != null ? toF(weather.temp) : "--"}°F
                </div>
                <div class="text-muted">${weather.condition ?? "Unknown"}</div>
            </div>
            <div style="text-align:right;">
                <div>🌧 ${weather.will_rain ? "Rain likely" : "No rain"}</div>
                <div class="text-muted">${weather.is_raining_now ? "Raining now" : "Clear"}</div>
            </div>
        </div>
    `;

}

loadAnalytics();

</script>

</body>
</html>
"""

    return HTMLResponse(
        html
        .replace("{title}", title)
        .replace("{bed_id}", bed_id)
    )
@router.get("/device/{bed_id}", response_class=HTMLResponse, tags=["System"])
def device_page(bed_id: str, db: Session = Depends(get_db)):

    meta = db.query(BedMetaDB).filter(BedMetaDB.bed_id == bed_id).first()
    name = meta.name if meta and meta.name else bed_id
    icon = meta.icon if meta and meta.icon else "🌱"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>{icon} {name} · Device</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

 <style>
     body {{
    background:#0f1115;
    color:#ffffff;
    font-family: system-ui;
}}

/* Global text rules */
p, span, div, h1, h2, h3, h4, h5, li{{
    color:#ffffff;
}}

/* Muted / secondary text */
.small,
.text-muted {{
    color: rgba(255,255,255,0.65) !important;
}}

/* Links */
a {{
    color:#00ff9a;
}}
a:hover {{
    color:#00c77a;
}}

/* Cards */
.card {{
    background:#1b1f2a;
    border:1px solid #2a2f3a;
    color:#ffffff;
}}

/* Navbar */
.navbar {{
    background:#000;
    border-bottom:1px solid #2a2f3a;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px;
    align-items: stretch;
}}

.node-card {{
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}

/* Status colors */
.status-good {{ color:#00ff9a; font-weight:bold; }}
.status-warn {{ color:#ffcc00; font-weight:bold; }}
.status-bad  {{color:#ff4d4d; font-weight:bold; }}

/* Utility */
.grid {{
    display:grid;
    gap:10px;
}}

body {{
            background: radial-gradient(circle at top, #151922, #0f1115);
            color: #e6eaf2;
            font-family: system-ui, sans-serif;
        }}

        .card {{
            background: linear-gradient(145deg, #1b1f2a, #141821);
            border: 1px solid #2a2f3a;
            border-radius: 18px;
            margin-bottom: 14px;
        }}

        .chart-wrap {{
            position: relative;
            height: 320px;
        }}

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
        }}

        .stat {{
            background: #12151c;
            padding: 12px;
            border-radius: 12px;
            text-align: center;
        }}

        .weather-main {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .temp {{
            font-size: 42px;
            font-weight: bold;
        }}

      
    </style>
</head>

<body>

<nav class="navbar navbar-dark bg-black border-bottom border-secondary">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">🌱 Smart Garden</a>
    <a class="nav-link text-white" href="/nodes">← Back to Nodes</a>
  </div>
</nav>

<div class="container py-4">

<h2>{icon} {name}</h2>

<div id="status" class="card">Loading...</div>

<div class="grid">

    <div class="card">
        <div class="small">IP Address</div>
        <h5 id="ip">-</h5>
    </div>

    <div class="card">
        <div class="small">RSSI</div>
        <h5 id="rssi">-</h5>
    </div>

    <div class="card">
        <div class="small">Battery</div>
        <h5 id="battery">-</h5>
    </div>

    <div class="card">
        <div class="small">Valve</div>
        <h5 id="valve">-</h5>
    </div>

</div>

<div class="card">
    <h5>📡 RSSI History</h5>
    <div class="chart-wrap">
        <canvas id="rssiChart"></canvas>
    </div>
</div>

<div class="card">
    <h5>🚰 Valve History</h5>
    <div class="chart-wrap">
        <canvas id="valveChart"></canvas>
    </div>
</div>




</div>

<script>

let rssiChart = null;
let valveChart = null;

async function load() {{

    const res = await fetch("/api/beds/latest");
    const data = await res.json();

    const b = data["{bed_id}"];
    if (!b) return;

    document.getElementById("ip").innerText = b.ip ?? "unknown";
    document.getElementById("rssi").innerText = b.rssi ?? "N/A";
    document.getElementById("battery").innerText =
        b.battery ? b.battery.toFixed(2) + "V" : "N/A";

    document.getElementById("valve").innerText = b.valve_state ?? "OFF";

    const now = Date.now();
    const lastSeen = b.last_seen ? new Date(b.last_seen).getTime() : now;
    const online = (now - lastSeen) < 15000;

    document.getElementById("status").innerHTML =
        online
        ? "<span class='good'>🟢 ONLINE</span>"
        : "<span class='bad'>🔴 OFFLINE</span>";

    // -------------------------
    // HISTORY
    // -------------------------
    const hist = await fetch("/api/beds/{bed_id}/full-graph").then(r => r.json());

    const timestamps = (hist.timestamps || []).map(t =>
        new Date(t).toLocaleTimeString()
    );

    const rssi = (hist.rssi || []).map(v => Number(v));
    const valve = (hist.valve || []).map(v => Number(v));

    const minLen = Math.min(timestamps.length, rssi.length, valve.length);

    const labels = timestamps.slice(0, minLen);
    const rssiData = rssi.slice(0, minLen);
    const valveData = valve.slice(0, minLen);

    // -------------------------
    // RSSI CHART
    // -------------------------
    if (rssiChart) rssiChart.destroy();

    rssiChart = new Chart(document.getElementById("rssiChart"), {{
        type: "line",
        data: {{
            labels,
            datasets: [{{
                label: "RSSI (dBm)",
                data: rssiData,
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                y: {{
                    suggestedMin: -100,
                    suggestedMax: -30
                }}
            }}
        }}
    }});

    // -------------------------
    // VALVE CHART (FIXED + STEP SIGNAL)
    // -------------------------
    if (valveChart) valveChart.destroy();

    valveChart = new Chart(document.getElementById("valveChart"), {{
        type: "line",
        data: {{
            labels,
            datasets: [{{
                label: "Valve (1 = ON, 0 = OFF)",
                data: valveData,
                borderWidth: 2,
                pointRadius: 0,
                stepped: true,
                tension: 0,
                borderColor: "#00ff9a"
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                y: {{
                    min: 0,
                    max: 1,
                    ticks: {{
                        stepSize: 1
                    }}
                }}
            }}
        }}
    }});

}}

load();
setInterval(load, 3000);

</script>

</body>
</html>
"""

    return HTMLResponse(html)



#######################################
# Docs page
####################################### 
from fastapi.responses import HTMLResponse

@router.get("/app/docs", response_class=HTMLResponse, include_in_schema=False)
def embedded_docs():

    html = """
<!DOCTYPE html>
<html>
<head>
<title>🌱 Smart Irrigation · API Docs</title>

<link href="https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui.css" rel="stylesheet">

<style>
body {
    margin:0;
    background:#0f1115;
    color:white;
    font-family: system-ui;
}

/* Top navbar like your device page */
.navbar {
    background:#000;
    padding:12px 16px;
    border-bottom:1px solid #2a2f3a;
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.navbar a {
    color:white;
    text-decoration:none;
    margin-left:12px;
}

.header {
    padding:16px;
    font-size:20px;
    font-weight:600;
    border-bottom:1px solid #2a2f3a;
    background:#11131a;
}

/* Swagger container styling */
#swagger-ui {
    padding: 10px 20px 40px 20px;
}

/* Make swagger blend into dark UI */
.swagger-ui {
    filter: invert(92%) hue-rotate(180deg);
}

/* Fix ugly inverted code blocks */
.swagger-ui .highlight-code,
.swagger-ui code,
.swagger-ui pre {
    filter: invert(100%) hue-rotate(180deg);
}
</style>

</head>

<body>

<nav class="navbar">
    <div>🌱 Smart Garden API</div>
    <div>
        <a href="/">Dashboard</a>
        <a href="/nodes">Nodes</a>
        <a href="/app/docs">Docs</a>
    </div>
</nav>

<div class="header">
    📘 API Documentation
</div>

<div id="swagger-ui"></div>

<script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>

<script>
const ui = SwaggerUIBundle({
    url: "/openapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
    layout: "BaseLayout"
});
</script>

</body>
</html>
"""
    return HTMLResponse(html)


########################################
#login page
########################################

@router.get("/register", response_class=HTMLResponse)
def register_page():
    body = """
<div class="container py-5">

<h2>🌱 Create Account</h2>

<div class="card p-4">

<input id="email" class="form-control mb-2" placeholder="Email">
<input id="password" type="password" class="form-control mb-3" placeholder="Password">

<button class="btn btn-success w-100" onclick="register()">
    Create Account
</button>

<p class="mt-3 text-muted">
    Already have an account? <a href="/login">Login</a>
</p>

</div>

</div>

<script>

async function register() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch("/api/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ email, password })
    });

    if (res.ok) {
        window.location.href = "/setup-contact";
    } else {
        const err = await res.text();
        console.log(err);
        alert("Oopsie failed: " + err);
}
    }

</script>
"""
    return page("Register", body)



@router.get("/login", response_class=HTMLResponse)
def login_page():
    body = """
<div class="container py-5">

<h2>🔐 Login</h2>

<div class="card p-4">

<input id="email" class="form-control mb-2" placeholder="Email">
<input id="password" type="password" class="form-control mb-3" placeholder="Password">

<button class="btn btn-primary w-100" onclick="login()">
    Login
</button>

<p class="mt-3 text-muted">
    No account? <a href="/register">Register</a>
</p>

</div>

</div>

<script>

async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch("/api/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ email, password })
    });

    if (res.ok) {
        window.location.href = "/";
    } else {
        alert("invalid login :(");
    }
}

</script>
"""
    return page("Login", body)


from fastapi.responses import HTMLResponse
from fastapi.responses import HTMLResponse

from fastapi.responses import HTMLResponse

from fastapi.responses import HTMLResponse

@router.get("/setup-contact", response_class=HTMLResponse)
def setup_contact():
    body = """
<div class="container py-5">

    <h2>📱 Alert Setup</h2>
    <p class="text-muted">
        Set your phone number so the garden can notify you when watering happens.
    </p>

    <div class="card p-4">

        <label class="mb-1">Phone Number</label>
        <input id="phone" class="form-control mb-3" placeholder="+1 555 123 4567">

        <label class="mb-1">Carrier</label>
        <select id="carrier" class="form-control mb-3">
            <option value="">Loading carriers...</option>
        </select>

        <button class="btn btn-success w-100" onclick="save()">
            Save Alert Settings
        </button>

        <div id="status" class="mt-3 small text-muted"></div>

    </div>
</div>

<script>

async function loadCarriers() {
    try {
        const res = await fetch("/api/carriers", {
            credentials: "include"
        });

        if (!res.ok) throw new Error("Failed to fetch carriers");

        const data = await res.json();

        const select = document.getElementById("carrier");
        select.innerHTML = `<option value="">Select carrier</option>`;

        const carriers = Object.entries(data).map(([id, info]) => ({
            id,
            label: info.label   // ✅ FIX: use label, not object
        }));

        for (const c of carriers) {
            const opt = document.createElement("option");
            opt.value = c.id;
            opt.textContent = c.label; // ✅ FIXED HERE
            select.appendChild(opt);
        }

        if (carriers.length === 0) {
            select.innerHTML = `<option value="">No carriers found</option>`;
        }

    } catch (e) {
        console.error(e);
        document.getElementById("carrier").innerHTML =
            `<option value="">Failed to load carriers</option>`;
    }
}

async function loadExisting() {
    try {
        const res = await fetch("/api/user/contact", {
            credentials: "include"
        });

        if (!res.ok) return;

        const data = await res.json();

        if (data?.phone) {
            document.getElementById("phone").value = data.phone;
        }

        if (data?.carrier) {
            document.getElementById("carrier").value = data.carrier;
        }

    } catch (e) {
        console.log("No existing contact info");
    }
}

async function save() {
    const phone = document.getElementById("phone").value.trim();
    const carrier = document.getElementById("carrier").value;
    const status = document.getElementById("status");

    if (!phone || !carrier) {
        status.innerText = "⚠ Please enter phone + carrier";
        return;
    }

    status.innerText = "Saving...";

    try {
        const res = await fetch("/api/user/contact", {
            method: "POST",
            credentials: "include",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ phone, carrier })
        });

        if (!res.ok) {
            status.innerText = "❌ Failed to save";
            return;
        }

        status.innerText = "✅ Saved!";
        setTimeout(() => window.location.href = "/", 800);

    } catch (e) {
        status.innerText = "❌ Network error";
    }
}

loadCarriers();
loadExisting();

</script>
"""
    return page("Setup Contact", body)
@router.get("/notifications", response_class=HTMLResponse)
def notifications_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    if not user:
        return RedirectResponse("/login")

    body = """
<div class="container py-5">

    <h2>📱 Notifications</h2>
    <p class="text-muted">
        Manage how your garden sends you alerts across SMS, Discord, and Mobile Push.
    </p>

    <!-- 📞 SMS -->
    <div class="card p-4 mb-4">
        <h5>📞 SMS Alerts</h5>

        <div class="mb-3">
            <label>Phone Number</label>
            <input id="phone" class="form-control" placeholder="+1 555 123 4567">
        </div>

        <div class="mb-3">
            <label>Carrier</label>
            <select id="carrier" class="form-control">
                <option value="">Loading...</option>
            </select>
        </div>

        <button class="btn btn-success w-100" onclick="saveSMS()">
            Save SMS Settings
        </button>

        <button class="btn btn-outline-danger w-100 mt-2" onclick="clearContact()">
            Remove Number
        </button>
    </div>

    <!-- 🔥 PUSH -->
    <div class="card p-4 mb-4">
        <h5>📱 Mobile Push Notifications</h5>

        <p class="text-muted small">
            Get instant alerts on your phone when your plants need attention.
        </p>

        <div id="firebaseStatus" class="mb-3 text-muted">
            Checking push notification status...
        </div>

        <button class="btn btn-success w-100" onclick="enablePush()">
            🔔 Enable Push Notifications
        </button>

        <button class="btn btn-outline-danger w-100 mt-2" onclick="disablePush()">
            ❌ Disable Push Notifications
        </button>
    </div>

    <!-- 💬 DISCORD -->
    <div class="card p-4">
        <h5>💬 Discord Alerts</h5>

        <div id="discordStatus" class="mb-3 text-muted">
            Checking Discord connection...
        </div>

        <button class="btn btn-primary w-100" onclick="connectDiscord()">
            🔗 Connect Discord
        </button>

        <button class="btn btn-outline-danger w-100 mt-2" onclick="disconnectDiscord()">
            ❌ Disconnect Discord
        </button>
    </div>

    <div id="status" class="mt-3 text-muted small"></div>
</div>

<!-- FIREBASE -->
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js"></script>

<script>

// =========================
// 🔥 FIREBASE CONFIG
// =========================
const firebaseConfig = {
    apiKey: "AIzaSyBUGuSBZ59OyNlXO6msoY1XwJMZtirO3b0",
    authDomain: "smart-garden-4d476.firebaseapp.com",
    projectId: "smart-garden-4d476",
    messagingSenderId: "213616042233",
    appId: "1:213616042233:web:45360b3c4e2ef15ddb4228"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// =========================
// 🔥 SERVICE WORKER (FIXED SAFE LOAD)
// =========================
let swRegistration = null;

async function initSW() {
    if (!("serviceWorker" in navigator)) return null;

    if (swRegistration) return swRegistration;

    try {
        swRegistration = await navigator.serviceWorker.register(
            "/firebase-messaging-sw.js",
            { scope: "/" }
        );

        console.log("SW ready:", swRegistration.scope);
        return swRegistration;

    } catch (err) {
        console.error("SW registration failed:", err);
        return null;
    }
}

// =========================
// 🔑 VAPID KEY
// =========================
const VAPID_KEY = "BLilRiegS9xO-qceIAs_KQVtuPcOffCeI4UB6eTqvPpkhHVF0uNgyiJgNRLu2mVF3eiYrR_nip5JdO24YBkVcxg";

// =========================
// 🔥 GET TOKEN (FIXED RELIABILITY FLOW)
// =========================
async function getToken() {
    const sw = await initSW();

    if (!sw) return null;

    const permission = await Notification.requestPermission();
    if (permission !== "granted") return null;

    try {
        const token = await messaging.getToken({
            vapidKey: VAPID_KEY,
            serviceWorkerRegistration: sw
        });

        return token || null;

    } catch (err) {
        console.error("Token error:", err);
        return null;
    }
}

// =========================
// 📦 LOAD SETTINGS
// =========================
async function loadSettings() {
    const res = await fetch("/api/user/notifications", {
        credentials: "include"
    });

    const data = await res.json();

    document.getElementById("phone").value = data.phone || "";
    document.getElementById("carrier").value = data.carrier || "";

    document.getElementById("discordStatus").innerText =
        data.discord_user_id ? "🟢 Connected" : "🔴 Not connected";

    document.getElementById("firebaseStatus").innerText =
        data.firebase_token ? "🟢 Push enabled" : "🔴 Push disabled";
}

// =========================
// 💾 SAVE SMS
// =========================
async function saveSMS() {
    await fetch("/api/user/notifications", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        credentials: "include",
        body: JSON.stringify({
            phone: document.getElementById("phone").value,
            carrier: document.getElementById("carrier").value
        })
    });
}

// =========================
// 🔥 ENABLE PUSH
// =========================
async function enablePush() {
    const status = document.getElementById("firebaseStatus");

    try {
        status.innerText = "Initializing...";

        const token = await getToken();

        if (!token) {
            status.innerText = "❌ Failed to get device token";
            return;
        }

        status.innerText = "Saving device...";

        const res = await fetch("/api/user/firebase-token", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "include",
            body: JSON.stringify({ firebase_token: token })
        });

        status.innerText = res.ok
            ? "🟢 Push enabled"
            : "❌ Failed to save token";

        loadSettings();

    } catch (e) {
        console.error(e);
        status.innerText = "❌ Push error";
    }
}

// =========================
// 🔥 DISABLE PUSH
// =========================
async function disablePush() {
    await fetch("/api/user/firebase-token", {
        method: "DELETE",
        credentials: "include"
    });

    document.getElementById("firebaseStatus").innerText =
        "🔴 Push disabled";

    loadSettings();
}

// =========================
// 🚀 INIT (IMPORTANT FIX)
// =========================
window.addEventListener("load", async () => {
    await initSW();
    loadSettings();
});

</script>
"""
    return page("Notifications", body)
@router.get("/api-keys", response_class=HTMLResponse, tags=["System"])
def api_keys_page(
    request: Request,
    user: User = Depends(get_current_user)
):

    if not user:
        return RedirectResponse("/login")

    body = """
<body>

<div class="container py-4">

<h2 class="mb-3">🔐 API Key Management</h2>

<div class="alert alert-dark">
    Create, view, and revoke device API keys.
</div>

<!-- CREATE KEY -->
<div class="card p-3 mb-3">
    <h5>➕ Create New Key</h5>

    <input id="keyName" class="form-control mb-2" placeholder="Device name (e.g. bed_1)">

    <button class="btn btn-success" onclick="createKey()">
        Generate Key
    </button>

    <div id="newKeyBox" class="mt-3"></div>
</div>

<!-- KEY LIST -->
<div class="card p-3">
    <h5>🔑 Active Keys</h5>
    <div id="keys">Loading...</div>
</div>

</div>

<script>

/* -------------------------
   LOAD KEYS
------------------------- */
async function loadKeys() {
    try {
        const res = await fetch("/api/keys");
        const data = await res.json();

        let html = "";

        for (const k of data) {
            html += `
                <div class="border rounded p-2 mb-2">

                    <b>${k.name}</b><br>
                    <small>ID: ${k.id}</small><br>
                    <small>Active: ${k.active}</small>

                    <button class="btn btn-sm btn-danger mt-2"
                        onclick="revokeKey('${k.id}')">
                        Revoke
                    </button>

                </div>
            `;
        }

        document.getElementById("keys").innerHTML = html;

    } catch (e) {
        document.getElementById("keys").innerHTML =
            "⚠ Failed to load keys";
    }
}

/* -------------------------
   CREATE KEY
------------------------- */
async function createKey() {
    const name = document.getElementById("keyName").value;

    if (!name) return alert("Enter a name");

    const res = await fetch(`/api/keys/create?name=${encodeURIComponent(name)}`, {
        method: "POST"
    });

    const data = await res.json();

    document.getElementById("newKeyBox").innerHTML = `
        <div class="alert alert-success">
            <b>New API Key Created</b><br><br>
            <code>${data.api_key}</code><br><br>
            ⚠ Save this — it won't be shown again.
        </div>
    `;

    loadKeys();
}

/* -------------------------
   REVOKE KEY
------------------------- */
async function revokeKey(id) {
    if (!confirm("Revoke this key?")) return;

    await fetch(`/api/keys/${id}/revoke`, {
        method: "POST"
    });

    loadKeys();
}

/* -------------------------
   INIT
------------------------- */
(async function init() {
    loadKeys();
    setInterval(loadKeys, 5000);
})();

</script>

</body>
</html>
"""

    return page("API Keys", body)
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






# =====================================================
# 🌱 GLOBAL STYLES (MOBILE FIXED)
# =====================================================
GLOBAL_CSS = """
body {
    background: radial-gradient(circle at top, #151922, #0f1115);
    color: #e6eaf2;
    font-family: system-ui, sans-serif;
    margin: 0;
    padding: 0;
}

/* typography */
p, span, div, h1, h2, h3, h4, h5, li {
    color: #ffffff;
}

/* muted text */
.text-muted, .small {
    color: rgba(255,255,255,0.65) !important;
}

/* links */
a {
    color: #00ff9a;
}
a:hover {
    color: #00c77a;
}

/* cards */
.card {
    background: linear-gradient(145deg, #1b1f2a, #141821);
    border: 1px solid #2a2f3a;
    border-radius: 16px;
    color: white;
    margin-bottom: 12px;
    word-wrap: break-word;
}

/* layout helpers */
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
}

/* stats */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
}

.stat {
    background: #12151c;
    padding: 12px;
    border-radius: 12px;
    text-align: center;
}

/* navbar mobile fix */
.navbar {
    background: #000;
    border-bottom: 1px solid #2a2f3a;
}

.navbar-nav {
    gap: 8px;
}

/* responsive text */
h1,h2,h3,h4 {
    font-size: clamp(1.1rem, 3vw, 1.6rem);
}

/* =========================
   STATUS SYSTEM (GLOBAL FIX)
========================= */

.status-good {
    color: #00ff9a !important;
    font-weight: 700;
}

.status-warn {
    color: #ffcc00 !important;
    font-weight: 700;
}

.status-bad {
    color: #ff4d4d !important;
    font-weight: 700;
}

/* Optional: nicer badge look */
.badge.status-good {
    background: rgba(0, 255, 154, 0.12);
    border: 1px solid #00ff9a;
    color: #00ff9a;
}

.badge.status-warn {
    background: rgba(255, 204, 0, 0.12);
    border: 1px solid #ffcc00;
    color: #ffcc00;
}

.badge.status-bad {
    background: rgba(255, 77, 77, 0.12);
    border: 1px solid #ff4d4d;
    color: #ff4d4d;
}
"""

# =====================================================
# 🌐 MOBILE NAVBAR (FIXED)
# =====================================================
NAVBAR = """
<nav class="navbar navbar-expand-lg navbar-dark">
  <div class="container-fluid">

    <a class="navbar-brand" href="/">🌱 Smart Garden</a>

    <button class="navbar-toggler" type="button"
        data-bs-toggle="collapse" data-bs-target="#navMenu">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="collapse navbar-collapse" id="navMenu">
      <div class="navbar-nav ms-auto">

        <a class="nav-link" href="/">Dashboard</a>
        <a class="nav-link" href="/nodes">🌿 Devices</a>
        <a class="nav-link" href="/notifications">📱 Notifications</a>
        <a class="nav-link" href="/api-keys">🔐 API Keys</a>
        <a class="nav-link" href="/app/docs">API Docs</a>
        <a class="nav-link" href="/about">About</a>
        <a class="nav-link" href="/logout">Logout</a>

      </div>
    </div>

  </div>
</nav>
"""

# =====================================================
# 📄 BASE PAGE WRAPPER (FIXED MOBILE META)
# =====================================================
def page(title: str, body: str):
    return f"""
<!DOCTYPE html>
<html>
<head>
<title>{title}</title>

<meta name="viewport" content="width=device-width, initial-scale=1">

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

<div class="container py-3">
{body}
</div>

<footer style="text-align:center;padding:20px;color:#9aa4b2;border-top:1px solid #2a2f3a;margin-top:40px;">
Made with 💖 Nicky Blackburn
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

</body>
</html>
"""
@router.get("/", response_class=HTMLResponse, tags=["System"])
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    if not user:
        return RedirectResponse("/login")

    body = """

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
   WEATHER
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
   STATUS (UNCHANGED LOGIC)
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
   SELECT BED
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

        for (const b of Object.values(latest)) {

            let life = {};
            try {
                life = await fetch(`/api/beds/${b.bed_id}/lifetime`).then(r => r.json());
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

                    <div class="mt-2">
                        <span class="badge ${status.cls}">
                            ${status.text}
                        </span>
                    </div>

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
@router.get("/bed/{bed_id}/analytics", response_class=HTMLResponse, tags=["System"])
def bed_analytics_page(bed_id: str, db: Session = Depends(get_db)):

    meta = db.query(BedMetaDB).filter(BedMetaDB.bed_id == bed_id).first()

    bed_name = meta.name if meta and meta.name else bed_id
    bed_icon = meta.icon if meta and meta.icon else "🌱"
    title = f"{bed_icon} {bed_name} Analytics"

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>

    <!-- ✅ MOBILE FIX -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
body {{
    background: radial-gradient(circle at top, #151922, #0f1115);
    color:#ffffff;
    font-family: system-ui;
    margin: 0;
    padding: 0;
}}

p, span, div, h1, h2, h3, h4, h5, li {{
    color:#ffffff;
}}

.text-muted {{
    color: rgba(255,255,255,0.65) !important;
}}

a {{ color:#00ff9a; }}
a:hover {{ color:#00c77a; }}

.card {{
    background: linear-gradient(145deg, #1b1f2a, #141821);
    border: 1px solid #2a2f3a;
    border-radius: 18px;
    margin-bottom: 14px;
    color:#ffffff;
}}

.navbar {{
    background:#000;
    border-bottom:1px solid #2a2f3a;
}}

.chart-wrap {{
    position: relative;
    height: 320px;
    width: 100%;
}}

canvas {{
    width: 100% !important;
    height: 100% !important;
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

.status-good {{ color:#00ff9a; font-weight:bold; }}
.status-warn {{ color:#ffcc00; font-weight:bold; }}
.status-bad  {{ color:#ff4d4d; font-weight:bold; }}

/* =========================
   ✅ MOBILE FIXES
========================= */
@media (max-width: 768px) {{

    .chart-wrap {{
        height: 220px;
    }}

    .temp {{
        font-size: 32px;
    }}

    h2 {{
        font-size: 20px;
    }}

    .stat-grid {{
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
    }}

    .navbar-nav {{
        flex-wrap: wrap;
        gap: 6px;
    }}

    .nav-link {{
        font-size: 13px;
        padding: 4px 6px;
    }}
}}

    </style>
</head>

<body>

<nav class="navbar navbar-dark bg-black border-bottom border-secondary">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">🌱 Smart Garden</a>
    <a class="nav-link text-white" href="/">← Back to Bed view</a>
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

function toF(c) {{
    return Math.round((c * 9/5) + 32);
}}

async function loadAnalytics() {{

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

    let status = health?.status ?? "unknown";

    const allowedStatuses = ["healthy", "warning", "bad"];

    if (!allowedStatuses.includes(status)) {{
        status = "unknown";
    }}

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

    if (moistureChart) moistureChart.destroy();

    moistureChart = new Chart(document.getElementById("moistureChart"), {{
        type: "line",
        data: {{
            labels,
            datasets: [{{
                label: "Moisture",
                data: safeMoisture,
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.4
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false
        }}
    }});

    if (healthChart) healthChart.destroy();

    healthChart = new Chart(document.getElementById("healthChart"), {{
        type: "line",
        data: {{
            labels,
            datasets: [{{
                label: "Plant Health",
                data: safeHealth,
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.4,
                borderColor: "#00ff9a",
                fill: true
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                y: {{ min: 0, max: 100 }}
            }}
        }}
    }});

    document.getElementById("weatherBox").innerHTML = `
        <div class="weather-main">
            <div>
                <div class="temp">
                    ${{weather.temp != null ? toF(weather.temp) : "--"}}°F
                </div>
                <div class="text-muted">${{weather.condition ?? "Unknown"}}</div>
            </div>
            <div style="text-align:right;">
                <div>🌧 ${{weather.will_rain ? "Rain likely" : "No rain"}}</div>
                <div class="text-muted">${{weather.is_raining_now ? "Raining now" : "Clear"}}</div>
            </div>
        </div>
    `;

}}

loadAnalytics();

window.addEventListener("resize", () => {{
    if (moistureChart) moistureChart.resize();
    if (healthChart) healthChart.resize();
}});

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

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

body {{
    background: radial-gradient(circle at top, #151922, #0f1115);
    color: #e6eaf2;
    font-family: system-ui, sans-serif;
    margin: 0;
    padding: 0;
}}

/* TEXT */
p, span, div, h1, h2, h3, h4, h5, li {{
    color: #e6eaf2;
}}

.small, .text-muted {{
    color: rgba(255,255,255,0.65) !important;
}}

/* LINKS */
a {{
    color:#00ff9a;
}}

/* CARDS */
.card {{
    background: linear-gradient(145deg, #1b1f2a, #141821);
    border: 1px solid #2a2f3a;
    border-radius: 16px;
    padding: 12px;
}}

/* NAV */
.navbar {{
    background:#000;
    border-bottom:1px solid #2a2f3a;
}}

/* GRID (FIXED FOR MOBILE) */
.grid {{
    display:grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap:10px;
}}

/* STATUS */
.status-good {{ color:#00ff9a; font-weight:bold; }}
.status-warn {{ color:#ffcc00; font-weight:bold; }}
.status-bad  {{ color:#ff4d4d; font-weight:bold; }}

/* CHART WRAPPER (MOBILE FIX) */
.chart-wrap {{
    position: relative;
    height: 260px;
}}

@media (max-width: 768px) {{
    .chart-wrap {{
        height: 200px;
    }}

    h2 {{
        font-size: 20px;
    }}

    .temp {{
        font-size: 32px;
    }}
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

<div class="container py-3">

<h2>{icon} {name}</h2>

<div id="status" class="card mb-3">Loading...</div>

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

<div class="card mt-3">
    <h5>📡 RSSI History</h5>
    <div class="chart-wrap">
        <canvas id="rssiChart"></canvas>
    </div>
</div>

<div class="card mt-3">
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
        ? "<span class='status-good'>🟢 ONLINE</span>"
        : "<span class='status-bad'>🔴 OFFLINE</span>";

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
            Manage how your garden sends you alerts across Discord and Mobile Push.
        </p>

        <!-- 🔥 PUSH -->
        <div class="card p-4 mb-4">
            <h5>📱 Mobile Push Notifications</h5>

            <p class="text-muted small">
                Get instant alerts when your plants need attention.
            </p>

            <div id="firebaseStatus" class="mb-2 text-muted">
                Loading push status...
            </div>

            <table class="table table-dark table-sm mb-3">
                <thead>
                    <tr>
                        <th>Device</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="firebaseTableBody">
                    <tr>
                        <td colspan="3" class="text-muted">Loading devices...</td>
                    </tr>
                </tbody>
            </table>

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
                Loading Discord status...
            </div>

            <button class="btn btn-primary w-100" onclick="connectDiscord()">
                🔗 Connect Discord
            </button>

            <button class="btn btn-outline-danger w-100 mt-2" onclick="disconnectDiscord()">
                ❌ Disconnect Discord
            </button>
        </div>

    </div>

    <script>

    // =========================
    // FIREBASE SAFE INIT
    // =========================
    (function ensureFirebaseInit() {
        if (!window.firebase) return;

        if (!firebase.apps || firebase.apps.length === 0) {
            firebase.initializeApp({
                apiKey: "AIzaSyBuGuSBZ59OyNlXO6msoX9WJMZtirO3b0",
                authDomain: "smart-garden-4d476.firebaseapp.com",
                projectId: "smart-garden-4d476",
                storageBucket: "smart-garden-4d476.firebasestorage.app",
                messagingSenderId: "213616042233",
                appId: "1:213616042233:web:45360b3c4e2ef15ddb4228",
                measurementId: "G-SY1BBH1LLJ"
            });
        }
    })();

    async function initSW() {
        if (!("serviceWorker" in navigator)) return null;

        try {
            let reg = await navigator.serviceWorker.getRegistration();
            if (reg) return reg;

            return await navigator.serviceWorker.register(
                "/firebase-messaging-sw.js",
                { scope: "/" }
            );

        } catch (err) {
            console.error(err);
            return null;
        }
    }

    async function getTokenSafe() {
        try {
            const permission = await Notification.requestPermission();
            if (permission !== "granted") return null;

            const sw = await initSW();
            if (!sw) return null;

            const messaging = firebase.messaging();

            return await messaging.getToken({
                vapidKey:
                    "BLilRiegS9xO-qceIAs_KQVtuPcOffCeI4UB6eTqvPpkhHVF0uNgyiJgNRLu2mVF3eiYrR_nip5JdO24YBkVcxg",
                serviceWorkerRegistration: sw
            });

        } catch (err) {
            console.error(err);
            return null;
        }
    }

    async function loadSettings() {
        try {
            const res = await fetch("/api/user/notifications?t=" + Date.now(), {
                credentials: "include"
            });

            const data = await res.json();

            const tokens = Array.isArray(data.firebase_tokens)
                ? data.firebase_tokens
                : [];

            document.getElementById("firebaseStatus").innerText =
                tokens.length
                    ? `🟢 ${tokens.length} device(s) connected`
                    : "🔴 No devices connected";

            const tbody = document.getElementById("firebaseTableBody");
            tbody.innerHTML = "";

            if (!tokens.length) {
                tbody.innerHTML =
                    `<tr><td colspan="3" class="text-muted">No devices registered</td></tr>`;
            } else {
                tokens.forEach(t => {
                    const token = typeof t === "string" ? t : t.token;

                    tbody.innerHTML += `
                        <tr>
                            <td>${token.substring(0, 28)}...</td>
                            <td>🟢 Active</td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger"
                                    onclick="removeToken('${token}')">
                                    Remove
                                </button>
                            </td>
                        </tr>
                    `;
                });
            }

            document.getElementById("discordStatus").innerText =
                data.discord_user_id
                    ? "🟢 Connected"
                    : "🔴 Not connected";

        } catch (err) {
            console.error(err);
        }
    }

    async function removeToken(token) {
        await fetch("/api/firebase/firebase-token", {
            method: "DELETE",
            headers: {"Content-Type": "application/json"},
            credentials: "include",
            body: JSON.stringify({ token })
        });

        await loadSettings();
    }

    async function enablePush() {
        const token = await getTokenSafe();
        if (!token) return;

        await fetch("/api/firebase/firebase-token", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "include",
            body: JSON.stringify({ firebase_token: token })
        });

        await loadSettings();
    }

    async function disablePush() {
        await fetch("/api/firebase/firebase-token", {
            method: "DELETE",
            credentials: "include"
        });

        await loadSettings();
    }

    function connectDiscord() {
        window.location.href = "/api/discord/connect";
    }

    async function disconnectDiscord() {
        await fetch("/api/discord/disconnect", {
            method: "DELETE",
            credentials: "include"
        });

        await loadSettings();
    }

    window.addEventListener("load", async () => {
        await initSW();
        await loadSettings();
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




























@router.get("/app/docs", response_class=HTMLResponse, tags=["System"])
def custom_docs():

    html = """
<!DOCTYPE html>
<html>
<head>
    <title>🌱 Smart Garden API Docs</title>

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <style>

body {
    margin: 0;
    background: radial-gradient(circle at top, #151922, #0f1115);
    color: #e6eaf2;
    font-family: system-ui;
}

/* NAV */
.navbar {
    background:#000;
    border-bottom:1px solid #2a2f3a;
}

/* HEADER */
.header {
    padding: 20px;
    text-align: center;
}

/* SWAGGER WRAPPER */
.swagger-wrap {
    height: calc(100vh - 140px);
    width: 100%;
    border: none;
    border-radius: 12px;
    overflow: hidden;
    background: #1b1f2a;
}

/* MOBILE FIX */
@media (max-width: 768px) {
    .header h2 {
        font-size: 18px;
    }

    .header p {
        font-size: 13px;
    }

    .swagger-wrap {
        height: calc(100vh - 120px);
    }
}

    </style>
</head>

<body>

<nav class="navbar navbar-dark bg-black border-bottom border-secondary">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">🌱 Smart Garden</a>
    <a class="nav-link text-white" href="/">← Back to Dashboard</a>
  </div>
</nav>

<div class="header">
    <h2>📘 API Documentation</h2>
    <p class="text-muted">Interactive Smart Garden API (Swagger UI)</p>
</div>

<div class="container-fluid">
    <iframe
        class="swagger-wrap"
        src="/docs"
    ></iframe>
</div>

</body>
</html>
"""

    return HTMLResponse(html)
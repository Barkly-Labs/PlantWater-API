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

# ============================================================
# HTML CONSTANTS
# ============================================================

GLOBAL_CSS = """
body {
    background:#0f1115;
    color:#ffffff;
    font-family: system-ui;
}

p, span, div, h1, h2, h3, h4, h5, li {
    color:#ffffff;
}

.small, .text-muted {
    color: rgba(255,255,255,0.65) !important;
}

a {
    color:#00ff9a;
}
a:hover {
    color:#00c77a;
}

.card {
    background:#1b1f2a;
    border:1px solid #2a2f3a;
    color:#ffffff;
}

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

.status-good { color:#00ff9a; font-weight:bold; }
.status-warn { color:#ffcc00; font-weight:bold; }
.status-bad  { color:#ff4d4d; font-weight:bold; }

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
      <a class="nav-link" href="/app/docs">API Docs</a>
      <a class="nav-link" href="/about">About</a>
      <a class="nav-link" href="/logout">Logout</a>
    </div>
  </div>
</nav>
"""


def page(title: str, body: str):
    """Build HTML page with navbar and styling"""
    return f"""
<!DOCTYPE html>
<html>
<head>
<title>{title}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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


# ============================================================
# DASHBOARD PAGE
# ============================================================

@router.get("/", response_class=HTMLResponse, tags=["Pages"])
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Main dashboard page with garden status"""
    if not user:
        return RedirectResponse("/login")
    
    body = """
<div class="container py-4">
<h2 class="mb-3">🌿 Garden Control Panel</h2>
<div id="weather" class="alert alert-info">Loading weather...</div>
<div class="row" id="beds"></div>
</div>
<script>
let bedMeta = {};
async function loadMeta() {
    try {
        const res = await fetch("/api/beds/meta");
        bedMeta = await res.json();
    } catch (e) {
        bedMeta = {};
    }
}
async function loadWeather() {
    try {
        const res = await fetch('/api/weather');
        const data = await res.json();
        document.getElementById("weather").innerText = data.is_raining_now ? "🌧 Currently raining" : data.will_rain ? "🌧 Rain expected soon" : "☀ Stable conditions";
    } catch (e) {
        document.getElementById("weather").innerText = "⚠ Weather unavailable";
    }
}
function getStatus(avg) {
    if (avg > 700) return { text:"DRY", cls:"status-bad" };
    if (avg < 300) return { text:"WET", cls:"status-warn" };
    return { text:"HEALTHY", cls:"status-good" };
}
function goToBed(bedId) {
    window.location.href = `/bed/${bedId}/analytics`;
}
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
                <div class="card p-3" onclick="goToBed('${b.bed_id}')">
                    <h5>${icon} ${name}</h5>
                    <div class="small">ID: ${b.bed_id}</div>
                    <button class="btn btn-sm btn-outline-light mt-2" onclick="event.stopPropagation(); editBed('${b.bed_id}')">✏ Edit</button>
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
        document.getElementById("beds").innerHTML = "<p>⚠ Failed to load beds</p>";
    }
}
(async function init() {
    await loadMeta();
    await loadBeds();
    await loadWeather();
    setInterval(loadBeds, 3000);
    setInterval(loadWeather, 10000);
})();
</script>
"""
    return page("Dashboard", body)


@router.get("/nodes", response_class=HTMLResponse, tags=["Pages"])
def node_status_page(user: User = Depends(get_current_user)):
    """Device status page"""
    if not user:
        return RedirectResponse("/login")
    
    body = """
<div class="container py-4">
<h2 class="mb-3">🛰 Garden Node Status</h2>
<div id="nodes" class="grid"></div>
</div>
<script>
let meta = {};
async function loadMeta() {
    const res = await fetch("/api/beds/meta");
    meta = await res.json();
}
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
<a class="node-link" href="/device/${bedId}" style="text-decoration:none;">
    <div class="card node-card p-3">
        <h5>${icon} ${name}</h5>
        <div class="small">ID: ${bedId}</div>
        <div class="small">IP: ${n.ip ?? "unknown"}</div>
        <p class="${rssiClass}">📡 RSSI: ${n.rssi ?? "?"} dBm</p>
        <p>🔋 Battery: ${n.battery ? n.battery.toFixed(2) + "V" : "N/A"}</p>
        <p>💧 Moisture: ${n.average?.toFixed(1) ?? "?"}</p>
        <p>🚰 Valve: ${n.valve_state ?? "?"}</p>
    </div>
</a>
`;
    }
    document.getElementById("nodes").innerHTML = html;
}
(async function init() {
    await loadMeta();
    await loadNodes();
    setInterval(loadNodes, 3000);
})();
</script>
"""
    return page("Devices", body)


@router.get("/register", response_class=HTMLResponse, tags=["Pages"])
def register_page():
    """User registration page"""
    body = """
<div class="container py-5">
<h2>🌱 Create Account</h2>
<div class="card p-4">
<input id="email" class="form-control mb-2" placeholder="Email">
<input id="password" type="password" class="form-control mb-3" placeholder="Password">
<button class="btn btn-success w-100" onclick="register()">Create Account</button>
<p class="mt-3 text-muted">Already have an account? <a href="/login">Login</a></p>
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
        alert("Failed: " + await res.text());
    }
}
</script>
"""
    return page("Register", body)


@router.get("/login", response_class=HTMLResponse, tags=["Pages"])
def login_page():
    """User login page"""
    body = """
<div class="container py-5">
<h2>🔐 Login</h2>
<div class="card p-4">
<input id="email" class="form-control mb-2" placeholder="Email">
<input id="password" type="password" class="form-control mb-3" placeholder="Password">
<button class="btn btn-primary w-100" onclick="login()">Login</button>
<p class="mt-3 text-muted">No account? <a href="/register">Register</a></p>
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
        alert("Invalid login");
    }
}
</script>
"""
    return page("Login", body)


@router.get("/setup-contact", response_class=HTMLResponse, tags=["Pages"])
def setup_contact():
    """Setup contact info page"""
    body = """
<div class="container py-5">
<h2>📱 Alert Setup</h2>
<p class="text-muted">Set your phone number so the garden can notify you when watering happens.</p>
<div class="card p-4">
<label class="mb-1">Phone Number</label>
<input id="phone" class="form-control mb-3" placeholder="+1 555 123 4567">
<label class="mb-1">Carrier</label>
<select id="carrier" class="form-control mb-3">
    <option value="">Loading carriers...</option>
</select>
<button class="btn btn-success w-100" onclick="save()">Save Alert Settings</button>
<div id="status" class="mt-3 small text-muted"></div>
</div>
</div>
<script>
async function loadCarriers() {
    try {
        const res = await fetch("/api/carriers", { credentials: "include" });
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();
        const select = document.getElementById("carrier");
        select.innerHTML = `<option value="">Select carrier</option>`;
        for (const [id, info] of Object.entries(data)) {
            const opt = document.createElement("option");
            opt.value = id;
            opt.textContent = info.label;
            select.appendChild(opt);
        }
    } catch (e) {
        document.getElementById("carrier").innerHTML = `<option value="">Failed to load</option>`;
    }
}
async function loadExisting() {
    try {
        const res = await fetch("/api/user/contact", { credentials: "include" });
        if (!res.ok) return;
        const data = await res.json();
        if (data?.phone) document.getElementById("phone").value = data.phone;
        if (data?.carrier) document.getElementById("carrier").value = data.carrier;
    } catch (e) {}
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
            status.innerText = "❌ Failed";
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


@router.get("/notifications", response_class=HTMLResponse, tags=["Pages"])
def notifications_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Notifications management page"""
    if not user:
        return RedirectResponse("/login")
    
    body = """
<div class="container py-5">
<h2>📱 Notifications</h2>
<p class="text-muted">Manage how your garden sends you alerts.</p>
<div class="card p-4">
<div class="mb-3">
    <label>Current Phone</label>
    <input id="phone" class="form-control" placeholder="+1 555 123 4567">
</div>
<div class="mb-3">
    <label>Carrier</label>
    <select id="carrier" class="form-control">
        <option value="">Loading...</option>
    </select>
</div>
<button class="btn btn-success w-100" onclick="save()">Save Settings</button>
<button class="btn btn-outline-danger w-100 mt-2" onclick="clearContact()">Remove Number</button>
<div id="status" class="mt-3 text-muted small"></div>
</div>
</div>
<script>
async function loadCarriers() {
    const res = await fetch("/api/carriers", { credentials: "include" });
    const data = await res.json();
    const select = document.getElementById("carrier");
    select.innerHTML = `<option value="">Select carrier</option>`;
    for (const [id, info] of Object.entries(data)) {
        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = info.label;
        select.appendChild(opt);
    }
}
async function loadSettings() {
    const res = await fetch("/api/user/notifications", { credentials: "include" });
    const data = await res.json();
    if (data.phone) document.getElementById("phone").value = data.phone;
    if (data.carrier) document.getElementById("carrier").value = data.carrier;
}
async function save() {
    const phone = document.getElementById("phone").value;
    const carrier = document.getElementById("carrier").value;
    const status = document.getElementById("status");
    status.innerText = "Saving...";
    const res = await fetch("/api/user/notifications", {
        method: "POST",
        credentials: "include",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ phone, carrier })
    });
    if (!res.ok) {
        status.innerText = "❌ Failed";
        return;
    }
    status.innerText = "✅ Saved!";
}
async function clearContact() {
    document.getElementById("phone").value = "";
    document.getElementById("carrier").value = "";
    await save();
}
loadCarriers();
loadSettings();
</script>
"""
    return page("Notifications", body)


@router.get("/about", response_class=HTMLResponse, tags=["Pages"])
def about_page():
    """About page"""
    body = """
<div class="container py-5">
<div class="hero">
    <h1>🌱 Smart Garden System</h1>
    <p style="color: #ffffff;">IoT irrigation system with weather-aware automation</p>
</div>
<div class="card p-4 mb-4">
    <h4>📌 Project Overview</h4>
    <p>Smart irrigation network using FastAPI, ESP32 bed modules, and real-time dashboard.</p>
</div>
<div class="card p-4 mb-4">
    <h4>⚙️ Tech Stack</h4>
    <p>FastAPI · SQLite · SQLAlchemy · Chart.js · Bootstrap · ESP32 · OpenWeather API</p>
</div>
<div class="card p-4 mb-4">
    <h4>🌿 Features</h4>
    <ul>
        <li>Real-time soil moisture monitoring</li>
        <li>Automatic watering decision engine</li>
        <li>Weather-aware irrigation logic</li>
        <li>Historical sensor data storage</li>
        <li>Configurable watering thresholds</li>
    </ul>
</div>
<div class="text-center mt-4">
    <a href="/" class="btn btn-outline-light">← Back to Dashboard</a>
</div>
</div>
"""
    return page("About", body)


@router.get("/app/docs", response_class=HTMLResponse, tags=["Pages"])
def embedded_docs():
    """Embedded API documentation"""
    html = """
<!DOCTYPE html>
<html>
<head>
<title>🌱 Smart Irrigation · API Docs</title>
<link href="https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui.css" rel="stylesheet">
<style>
body { margin:0; background:#0f1115; color:white; font-family: system-ui; }
.navbar { background:#000; padding:12px 16px; border-bottom:1px solid #2a2f3a; display:flex; justify-content:space-between; align-items:center; }
.navbar a { color:white; text-decoration:none; margin-left:12px; }
.header { padding:16px; font-size:20px; font-weight:600; border-bottom:1px solid #2a2f3a; background:#11131a; }
#swagger-ui { padding: 10px 20px 40px 20px; }
.swagger-ui { filter: invert(92%) hue-rotate(180deg); }
.swagger-ui .highlight-code, .swagger-ui code, .swagger-ui pre { filter: invert(100%) hue-rotate(180deg); }
</style>
</head>
<body>
<nav class="navbar">
    <div>🌱 Smart Garden API</div>
    <div>
        <a href="/">Dashboard</a>
        <a href="/nodes">Nodes</a>
        <a href="/about">About</a>
    </div>
</nav>
<div class="header">📘 API Documentation</div>
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


@router.get("/bed/{bed_id}/analytics", response_class=HTMLResponse, tags=["Pages"])
def bed_analytics_page(bed_id: str, db: Session = Depends(get_db)):
    """Bed analytics page (stub - keep minimal)"""
    meta = db.query(BedMetaDB).filter(BedMetaDB.bed_id == bed_id).first()
    name = meta.name if meta and meta.name else bed_id
    icon = meta.icon if meta and meta.icon else "🌱"
    
    return HTMLResponse(f"""
<!DOCTYPE html>
<html><head>
<title>{icon} {name}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body {{ background:#0f1115; color:#ffffff; }}</style>
</head><body>
<div class="container py-4"><h2>{icon} {name}</h2><p>Analytics page</p></div>
</body></html>
""")


@router.get("/device/{bed_id}", response_class=HTMLResponse, tags=["Pages"])
def device_page(bed_id: str, db: Session = Depends(get_db)):
    """Device detail page (stub)"""
    meta = db.query(BedMetaDB).filter(BedMetaDB.bed_id == bed_id).first()
    name = meta.name if meta else bed_id
    icon = meta.icon if meta else "🌱"
    
    return HTMLResponse(f"""
<!DOCTYPE html>
<html><head>
<title>{icon} {name}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body {{ background:#0f1115; color:#ffffff; }}</style>
</head><body>
<div class="container py-4"><h2>{icon} {name}</h2><p>Device page</p></div>
</body></html>
""")

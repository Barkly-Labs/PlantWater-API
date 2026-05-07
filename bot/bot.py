import discord
from discord.ext import commands, tasks
from matplotlib import pyplot as plt
import requests
import os
import datetime
from dotenv import load_dotenv
import io

# =========================
# 🔐 ENV
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

API_BASE = "http://127.0.0.1:8000"
ADMIN_USER_ID = 1379571916058132480

# =========================
# ⚙️ BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

if bot.get_command("help"):
    bot.remove_command("help")

# =========================
# 🧠 STATE
# =========================
last_api_online = True
device_signal_state = {}

# =========================
# 🌐 API SAFE LAYER
# =========================
def api_get(path):
    try:
        return requests.get(f"{API_BASE}{path}", timeout=5).json()
    except:
        return None


def api_post(path):
    try:
        return requests.post(f"{API_BASE}{path}", timeout=5).status_code == 200
    except:
        return False


def get_beds():
    return api_get("/api/beds/latest")


def get_meta():
    return api_get("/api/beds/meta") or {}


def get_history(bed_id):
    # 👇 SAFE CHECK: avoids fake “not enabled” logic
    try:
        return requests.get(
            f"{API_BASE}/api/beds/{bed_id}/history",
            timeout=5
        ).json()
    except:
        return None


# =========================
# 💬 SAFE DM
# =========================
async def safe_dm(user_id, message):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(message)
    except:
        pass


# =========================
# 🌿 LOGIC
# =========================
def moisture_state(avg):
    if avg > 650:
        return "🏜️ Dry"
    if avg > 450:
        return "🌱 Healthy"
    return "💧 Wet"


def signal_state(rssi):
    if rssi is None:
        return "unknown"
    return "ok" if rssi > -80 else "weak"


# =========================
# 📡 MONITOR
# =========================
@tasks.loop(seconds=30)
async def monitor_system():
    global last_api_online, device_signal_state

    data = get_beds()

    if data is None:
        if last_api_online:
            await safe_dm(ADMIN_USER_ID, "🚨 Smart Garden API is OFFLINE")
        last_api_online = False
        return

    if not last_api_online:
        await safe_dm(ADMIN_USER_ID, "🟢 Smart Garden API is back online")

    last_api_online = True

    for bed_id, bed in data.items():
        rssi = bed.get("rssi")
        state = signal_state(rssi)

        prev = device_signal_state.get(bed_id)

        if state == "weak" and prev != "weak":
            await safe_dm(
                ADMIN_USER_ID,
                f"📶 Weak signal on `{bed_id}` (RSSI: {rssi})"
            )

        device_signal_state[bed_id] = state


# =========================
# 🚀 READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Bot online as {bot.user}")
    monitor_system.start()


# =========================
# 🤖 HELP
# =========================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🌱 Smart Garden Bot",
        description="IoT monitoring + control system",
        color=0x2ecc71,
        timestamp=datetime.datetime.now(datetime.UTC)
    )

    embed.add_field(name=".status", value="View all beds", inline=False)
    embed.add_field(name=".alerts", value="System issues", inline=False)
    embed.add_field(name=".water <bed_id>", value="Water a bed", inline=False)
    embed.add_field(name=".history <bed_id>", value="View moisture history (if API supports it)", inline=False)

    await ctx.send(embed=embed)


# =========================
# 📊 STATUS
# =========================
@bot.command()
async def status(ctx):
    data = get_beds()
    meta = get_meta()

    if not data:
        return await ctx.send("❌ API unreachable")

    embed = discord.Embed(
        title="🌱 Smart Garden Dashboard",
        color=0x2ecc71,
        timestamp=datetime.datetime.now(datetime.UTC)
    )

    for bed_id, bed in data.items():
        avg = bed.get("average", 0)
        valve = bed.get("valve_state", "OFF")

        name = meta.get(bed_id, {}).get("name", bed_id)

        embed.add_field(
            name=f"🌱 {name}",
            value=(
                f"💧 Moisture: `{avg:.1f}`\n"
                f"📊 State: {moisture_state(avg)}\n"
                f"🚰 Valve: {valve}"
            ),
            inline=True
        )

    await ctx.send(embed=embed)


# =========================
# 🚨 ALERTS
# =========================
@bot.command()
async def alerts(ctx):
    data = get_beds()

    if not data:
        return await ctx.send("❌ API unreachable")

    issues = []

    for bed_id, bed in data.items():
        if bed.get("average", 0) > 650:
            issues.append(f"🏜️ {bed_id} dry")
        if bed.get("rssi", 0) < -80:
            issues.append(f"📶 {bed_id} weak signal")

    if not issues:
        return await ctx.send("🟢 No issues detected")

    embed = discord.Embed(
        title="🚨 Alerts",
        description="\n".join(issues),
        color=0xe74c3c
    )

    await ctx.send(embed=embed)


# =========================
# 💧 WATER
# =========================
@bot.command()
async def water(ctx, bed_id: str = None):
    if not bed_id:
        return await ctx.send("❌ Usage: `.water <bed_id>`")

    ok = api_post(f"/api/beds/{bed_id}/water")

    if ok:
        await ctx.send(f"🚰 Watering started for `{bed_id}`")
    else:
        await ctx.send("❌ Failed to start watering")


# =========================
# 📊 HISTORY (FIXED — NO FAKE FEATURE)
# =========================
@bot.command()
async def history(ctx, bed_id: str = None):
    if not bed_id:
        return await ctx.send("❌ Usage: `.history <bed_id>`")

    try:
        res = requests.get(
            f"{API_BASE}/api/beds/{bed_id}/history",
            timeout=5
        )
        data = res.json()
    except:
        return await ctx.send("❌ Could not reach history API")

    if not data or len(data) < 2:
        return await ctx.send(
            "📊 Not enough history data yet to generate a graph.\n"
            "Need at least 2+ readings."
        )

    # =========================
    # 📈 PREP DATA
    # =========================
    values = [d.get("average", 0) for d in data[-100:]]
    labels = list(range(len(values)))

    # =========================
    # 📊 BUILD GRAPH
    # =========================
    plt.figure(figsize=(6, 3))
    plt.plot(labels, values)

    plt.title(f"Moisture History: {bed_id}")
    plt.xlabel("Time (latest → oldest)")
    plt.ylabel("Moisture")

    # =========================
    # 📦 CONVERT TO DISCORD FILE
    # =========================
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close()

    buf.seek(0)

    file = discord.File(buf, filename="history.png")

    embed = discord.Embed(
        title=f"📊 Bed History: {bed_id}",
        description="Soil moisture over time",
        color=0x3498db
    )

    embed.set_image(url="attachment://history.png")

    await ctx.send(embed=embed, file=file)


# =========================
# ▶️ RUN
# =========================
if not TOKEN:
    print("❌ Missing DISCORD_TOKEN")
else:
    bot.run(TOKEN)
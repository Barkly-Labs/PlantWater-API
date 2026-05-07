import discord
from discord.ext import commands, tasks
import requests
import os
import asyncio
import datetime
from dotenv import load_dotenv

# =========================
# 🔐 ENV
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

API_BASE = "http://127.0.0.1:8000"
ADMIN_USER_ID = 1379571916058132480  # <- your Discord ID

# =========================
# ⚙️ BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)
bot.remove_command("help")

# =========================
# 🧠 STATE TRACKING
# =========================
last_api_online = True
device_signal_state = {}

# =========================
# 🌐 API LAYER
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

# =========================
# 🌿 LOGIC
# =========================
def signal_state(rssi):
    if rssi is None:
        return "unknown"
    if rssi > -80:
        return "ok"
    return "weak"


# =========================
# 📡 MONITOR LOOP
# =========================
@tasks.loop(seconds=30)
async def monitor_system():
    global last_api_online, device_signal_state

    user = await bot.fetch_user(ADMIN_USER_ID)
    data = get_beds()

    # =========================
    # 🚨 API CHECK
    # =========================
    if data is None:
        if last_api_online:
            await user.send("🚨 Smart Garden API is OFFLINE")
        last_api_online = False
        return

    if not last_api_online:
        await user.send("🟢 Smart Garden API is back online")

    last_api_online = True

    # =========================
    # 📶 DEVICE SIGNAL CHECK
    # =========================
    for bed_id, bed in data.items():
        rssi = bed.get("rssi")
        state = signal_state(rssi)

        prev = device_signal_state.get(bed_id)

        if state == "weak" and prev != "weak":
            await user.send(f"📶 Weak signal on `{bed_id}` (RSSI: {rssi})")

        device_signal_state[bed_id] = state


# =========================
# 🚀 STARTUP
# =========================
@bot.event
async def on_ready():
    print(f"✅ Bot online as {bot.user}")
    monitor_system.start()


# =========================
# 🎨 EMBEDS
# =========================
def status_embed(data, meta):
    embed = discord.Embed(
        title="🌱 Smart Garden Dashboard",
        color=0x2ecc71,
        timestamp=datetime.datetime.utcnow()
    )

    for bed_id, bed in data.items():
        avg = bed.get("average", 0)
        valve = bed.get("valve_state", "OFF")

        name = meta.get(bed_id, {}).get("name", bed_id)

        embed.add_field(
            name=f"🌱 {name}",
            value=(
                f"💧 Moisture: `{avg:.1f}`\n"
                f"📊 State: {('🏜️ Dry' if avg > 650 else '🌱 Healthy' if avg > 450 else '💧 Wet')}\n"
                f"🚰 Valve: {valve}"
            ),
            inline=True
        )

    embed.set_footer(text="Smart Garden • Live System")
    return embed


# =========================
# 🤖 COMMANDS
# =========================
@bot.command()
async def status(ctx):
    data = get_beds()
    meta = get_meta()

    if not data:
        return await ctx.send("❌ API unreachable")

    await ctx.send(embed=status_embed(data, meta))


@bot.command()
async def water(ctx, bed_id: str):
    ok = api_post(f"/api/beds/{bed_id}/water")

    if ok:
        await ctx.send(f"🚰 Watering started for `{bed_id}`")
    else:
        await ctx.send("❌ Failed to start watering")


@bot.command()
async def alerts(ctx):
    data = get_beds()

    if not data:
        return await ctx.send("❌ API unreachable")

    issues = []

    for bed_id, bed in data.items():
        if bed.get("average", 0) > 650:
            issues.append(f"🏜️ {bed_id} is dry")
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
# ▶️ RUN
# =========================
if not TOKEN:
    print("❌ Missing DISCORD_TOKEN")
else:
    bot.run(TOKEN)
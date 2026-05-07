import discord
from discord.ext import commands
import requests
import os
import datetime
import asyncio
from dotenv import load_dotenv

# =========================
# 🔐 ENV
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

API_BASE = "http://127.0.0.1:8000"

# =========================
# ⚙️ BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)
bot.remove_command("help")


# =========================
# 🌐 API HELPERS
# =========================
def api_get(path):
    try:
        res = requests.get(f"{API_BASE}{path}", timeout=5)
        return res.json()
    except:
        return None


def api_post(path):
    try:
        res = requests.post(f"{API_BASE}{path}", timeout=5)
        return res.status_code == 200
    except:
        return False


def get_beds():
    return api_get("/api/beds/latest")


def get_meta():
    return api_get("/api/beds/meta") or {}


# =========================
# 🌱 STATUS CLASSIFIER
# =========================
def moisture_state(avg):
    if avg > 650:
        return "🏜️ Dry"
    elif avg > 450:
        return "🌱 Healthy"
    return "💧 Wet"


def signal_state(rssi):
    if rssi is None:
        return "❓ unknown"
    if rssi > -60:
        return "🟢 strong"
    if rssi > -75:
        return "🟡 medium"
    return "🔴 weak"


# =========================
# 🌿 HELP
# =========================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🌱 Smart Garden Bot v2",
        description="Control + monitor your irrigation system",
        color=0x2ecc71
    )

    embed.add_field(name=".status", value="Live sensor overview", inline=False)
    embed.add_field(name=".alerts", value="Show system issues", inline=False)
    embed.add_field(name=".water <bed_id>", value="Manually water a bed", inline=False)
    embed.add_field(name=".summary", value="Quick garden health summary", inline=False)
    embed.add_field(name=".live", value="Live updating status (short)", inline=False)

    embed.set_footer(text="Smart Garden • IoT Control System")

    await ctx.send(embed=embed)


# =========================
# 📊 STATUS
# =========================
@bot.command()
async def status(ctx):
    data = get_beds()
    meta = get_meta()

    if not data:
        await ctx.send("❌ API unreachable")
        return

    embed = discord.Embed(
        title="🌱 Smart Garden Status",
        description="Live sensor readings",
        color=0x3498db
    )

    active = []

    for bed_id, bed in data.items():
        avg = bed.get("average", 0)
        valve = bed.get("valve_state", "OFF")
        rssi = bed.get("rssi")

        name = meta.get(bed_id, {}).get("name", bed_id)
        icon = meta.get(bed_id, {}).get("icon", "🌱")

        embed.add_field(
            name=f"{icon} {name}",
            value=(
                f"Moisture: `{avg:.1f}`\n"
                f"State: {moisture_state(avg)}\n"
                f"Valve: {'🚰 ON' if valve == 'ON' else '🔒 OFF'}\n"
                f"Signal: {signal_state(rssi)}"
            ),
            inline=True
        )

        if valve == "ON":
            active.append(name)

    footer = f"🚰 Active: {', '.join(active)}" if active else "🟢 System idle"
    embed.set_footer(text=footer)

    await ctx.send(embed=embed)


# =========================
# 🚨 ALERTS
# =========================
@bot.command()
async def alerts(ctx):
    data = get_beds()

    if not data:
        await ctx.send("❌ API unreachable")
        return

    embed = discord.Embed(
        title="🚨 Garden Alerts",
        color=0xe74c3c
    )

    issues = 0

    for bed_id, bed in data.items():
        avg = bed.get("average", 0)
        rssi = bed.get("rssi", -999)

        problems = []

        if avg > 650:
            problems.append("🏜️ Soil too dry")
        if rssi < -80:
            problems.append("📶 Weak/unstable signal")

        if not problems:
            continue

        issues += 1
        embed.add_field(
            name=f"🌱 {bed_id}",
            value="\n".join(problems),
            inline=False
        )

    if issues == 0:
        embed.description = "🟢 Everything looks stable"

    embed.set_footer(text=f"{issues} issue(s) detected")

    await ctx.send(embed=embed)


# =========================
# 💧 MANUAL WATER
# =========================
@bot.command()
async def water(ctx, bed_id: str):
    ok = api_post(f"/api/beds/{bed_id}/water")

    if ok:
        await ctx.send(f"🚰 Watering started for `{bed_id}`")
    else:
        await ctx.send("❌ Failed to start watering")


# =========================
# 🌿 SUMMARY
# =========================
@bot.command()
async def summary(ctx):
    data = get_beds()

    if not data:
        await ctx.send("❌ API unreachable")
        return

    dry = []
    wet = []

    for bed_id, bed in data.items():
        avg = bed.get("average", 0)

        if avg > 650:
            dry.append(bed_id)
        elif avg < 350:
            wet.append(bed_id)

    msg = "🌱 **Garden Summary**\n"

    if dry:
        msg += f"🏜️ Dry: {', '.join(dry)}\n"
    if wet:
        msg += f"💧 Wet: {', '.join(wet)}\n"
    if not dry and not wet:
        msg += "🟢 Everything is stable"

    await ctx.send(msg)


# =========================
# 📡 LIVE MODE
# =========================
@bot.command()
async def live(ctx):
    msg = await ctx.send("🌱 Starting live feed...")

    for _ in range(10):
        data = get_beds()

        if not data:
            await msg.edit(content="❌ API offline")
            return

        lines = ["🌱 LIVE STATUS\n"]

        for bed_id, bed in data.items():
            avg = bed.get("average", 0)
            lines.append(f"{bed_id}: {avg:.1f}")

        await msg.edit(content="\n".join(lines))
        await asyncio.sleep(5)


# =========================
# 🤖 READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Connected as {bot.user}")


# =========================
# ▶️ RUN
# =========================
if not TOKEN:
    print("❌ Missing DISCORD_TOKEN in .env")
else:
    bot.run(TOKEN)
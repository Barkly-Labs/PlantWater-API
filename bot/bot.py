import discord
from discord.ext import commands, tasks
import requests
import os
import datetime
import io
import random
import matplotlib.pyplot as plt
from dotenv import load_dotenv

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


def get_history(bed_id):
    try:
        return requests.get(f"{API_BASE}/api/beds/{bed_id}/history", timeout=5).json()
    except:
        return None


# =========================
# 💬 SAFE DM
# =========================
async def safe_dm(user_id, msg):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(msg)
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
    return "🟢 ok" if rssi > -80 else "🔴 weak"


# =========================
# 📡 MONITOR LOOP
# =========================
@tasks.loop(seconds=30)
async def monitor_system():
    global last_api_online, device_signal_state

    data = get_beds()

    if data is None:
        if last_api_online:
            await safe_dm(ADMIN_USER_ID, "🚨 Smart Garden API OFFLINE")
        last_api_online = False
        return

    if not last_api_online:
        await safe_dm(ADMIN_USER_ID, "🟢 Smart Garden API BACK ONLINE")

    last_api_online = True

    for bed_id, bed in data.items():
        rssi = bed.get("rssi")
        state = signal_state(rssi)

        if device_signal_state.get(bed_id) != state and state == "🔴 weak":
            await safe_dm(ADMIN_USER_ID, f"📶 Weak signal: `{bed_id}` ({rssi})")

        device_signal_state[bed_id] = state


# =========================
# 🚀 READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Bot online as {bot.user}")
    monitor_system.start()


# =========================
# 🥚 EASTER EGGS
# =========================
EASTER_EGGS = {
    "plant": [
        "🌱 The plants are quietly judging you…",
        "💧 Soil whispers hydration secrets",
        "🌿 Growth detected everywhere"
    ],
    "cyn": [
        "🤖 The system is thinking too much",
        "⚠️ Garden AI awareness rising",
        "🌱 Optimization mode: unstable"
    ],
    "puppy": [
        "🐾 soft system tail wag detected",
        "🌱 garden accepts you warmly",
        "💚 emotional lettuce support active"
    ],
    "secret": [
        "🔒 nothing here… probably",
        "🌱 curiosity logged",
        "💧 hydration status: suspicious"
    ]
}


# =========================
# 🎨 DASHBOARD UI (NEW)
# =========================
class BedSelect(discord.ui.Select):
    def __init__(self, beds):
        options = [
            discord.SelectOption(label=bed_id, value=bed_id)
            for bed_id in beds.keys()
        ]

        super().__init__(
            placeholder="🌱 Select a bed...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_bed = self.values[0]
        await interaction.response.send_message(
            f"🌱 Selected `{self.values[0]}`",
            ephemeral=True
        )


class GardenDashboard(discord.ui.View):
    def __init__(self, beds):
        super().__init__(timeout=None)
        self.beds = beds
        self.selected_bed = None

        self.add_item(BedSelect(beds))

    # =========================
    # 📊 STATUS BUTTON
    # =========================
    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.green)
    async def status(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = get_beds()
        meta = get_meta()

        embed = discord.Embed(
            title="🌱 Live Garden Status",
            color=0x2ecc71
        )

        for bed_id, bed in data.items():
            embed.add_field(
                name=bed_id,
                value=f"💧 {bed.get('average', 0):.1f}",
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # =========================
    # 🚰 WATER BUTTON
    # =========================
    @discord.ui.button(label="🚰 Water", style=discord.ButtonStyle.blurple)
    async def water(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.selected_bed:
            return await interaction.response.send_message(
                "❌ Select a bed first",
                ephemeral=True
            )

        api_post(f"/api/beds/{self.selected_bed}/water")

        await interaction.response.send_message(
            f"🚰 Watering `{self.selected_bed}`",
            ephemeral=True
        )

    # =========================
    # 📈 HISTORY BUTTON
    # =========================
    @discord.ui.button(label="📈 History", style=discord.ButtonStyle.gray)
    async def history(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.selected_bed:
            return await interaction.response.send_message(
                "❌ Select a bed first",
                ephemeral=True
            )

        data = get_history(self.selected_bed)

        if not data:
            return await interaction.response.send_message(
                "❌ No history data",
                ephemeral=True
            )

        values = [d.get("average", 0) for d in data[-50:]]
        x = list(range(len(values)))

        plt.figure(figsize=(6, 3))
        plt.plot(x, values)
        plt.title(f"{self.selected_bed} history")

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()

        buf.seek(0)

        file = discord.File(buf, filename="history.png")

        embed = discord.Embed(
            title=f"📊 {self.selected_bed} History",
            color=0x3498db
        )

        embed.set_image(url="attachment://history.png")

        await interaction.response.send_message(
            embed=embed,
            file=file,
            ephemeral=True
        )


# =========================
# 🌿 DASHBOARD LAUNCH
# =========================
@bot.command()
async def dashboard(ctx):
    beds = get_beds()

    if not beds:
        return await ctx.send("❌ API unreachable")

    view = GardenDashboard(beds)

    embed = discord.Embed(
        title="🌱 Smart Garden Control Panel",
        description="Use dropdown + buttons below",
        color=0x2ecc71
    )

    await ctx.send(embed=embed, view=view)


# =========================
# 🤖 HELP (UPDATED)
# =========================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🌱 Smart Garden Bot",
        description="Now running in DASHBOARD MODE",
        color=0x2ecc71,
        timestamp=datetime.datetime.now(datetime.UTC)
    )

    embed.add_field(name="🧭 Main Command", value="`.dashboard` → Open full control panel", inline=False)
    embed.add_field(name="🥚 Easter Eggs", value="plant / cyn / puppy / secret", inline=False)

    await ctx.send(embed=embed)


# =========================
# ▶️ RUN
# =========================
if not TOKEN:
    print("❌ Missing DISCORD_TOKEN")
else:
    bot.run(TOKEN)
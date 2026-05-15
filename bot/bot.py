import asyncio
from asyncio import create_task

import discord
from discord.ext import commands, tasks
import requests
import os
import datetime
import io
import matplotlib.pyplot as plt
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
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        return r.json()
    except:
        return None


def api_post(path):
    try:
        return requests.post(f"{API_BASE}{path}", timeout=5).status_code == 200
    except:
        return False


def get_beds():
    return api_get("/api/beds/latest")


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
        user = await bot.fetch_user(int(user_id))
        await user.send(msg)
    except:
        pass


# =========================
# 📡 BACKEND POLLING (FIXED)
# =========================
async def poll_messages():
    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            r = requests.get(f"{API_BASE}/api/bot/poll", timeout=5)

            if r.status_code != 200:
                await asyncio.sleep(5)
                continue

            try:
                messages = r.json()
            except:
                messages = []

            if isinstance(messages, list):
                for msg in messages:
                    uid = msg.get("discord_user_id")
                    text = msg.get("message")

                    if uid and text:
                        await safe_dm(uid, text)

        except Exception as e:
            print("poll error:", e)

        await asyncio.sleep(5)


# =========================
# 🌿 LOGIC
# =========================
def signal_state(rssi):
    if rssi is None:
        return "unknown"
    return "🟢 ok" if rssi > -80 else "🔴 weak"


# =========================
# 📡 MONITOR LOOP (FIXED)
# =========================
@tasks.loop(seconds=30)
async def monitor_system():
    global last_api_online, device_signal_state

    data = get_beds()

    # API DOWN
    if data is None:
        last_api_online = False
        return

    # API BACK
    if not last_api_online:
        print("API back online")

    last_api_online = True

    # DEVICE MONITORING
    for bed_id, bed in data.items():
        rssi = bed.get("rssi")
        state = signal_state(rssi)

        if device_signal_state.get(bed_id) != state and state == "🔴 weak":
            print(f"Weak signal: {bed_id} ({rssi})")

        device_signal_state[bed_id] = state


# =========================
# 🚀 READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Bot online as {bot.user}")

    if not monitor_system.is_running():
        monitor_system.start()

    asyncio.create_task(poll_messages())


# =========================
# 🎨 DASHBOARD UI
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

    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.green)
    async def status(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = get_beds() or {}

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
# ▶️ RUN
# =========================
if not TOKEN:
    print("❌ Missing DISCORD_TOKEN")
else:
    bot.run(TOKEN)
import smtplib
import logging
import os
import requests

from email.mime.text import MIMEText
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

from dotenv import load_dotenv
from models import BedMetaDB, User, UserContact

load_dotenv()

# =========================================================
# 🌿 CONFIG
# =========================================================

logger = logging.getLogger("notifications")

SENDER_EMAIL = os.getenv("GARDEN_EMAIL")
SENDER_PASSWORD = os.getenv("GARDEN_PASSWORD")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

FIREBASE_SERVER_KEY = os.getenv("FIREBASE_SERVER_KEY", "")
FCM_URL = "https://fcm.googleapis.com/fcm/send"

DISCORD_QUEUE_URL = "http://127.0.0.1:8000/api/bot/queue"


# =========================================================
# 🌱 STATE TRACKING
# =========================================================

_last_state = {}
_last_alert_time: Dict[tuple, datetime] = {}


# =========================================================
# 🌿 EVENT SYSTEM
# =========================================================

class EventLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class GardenEvent:
    user_id: int
    bed_id: str
    type: str
    message: str
    level: EventLevel
    value: Optional[float] = None
    timestamp: datetime = datetime.utcnow()


# =========================================================
# 🌿 EMAIL
# =========================================================

def send_email(to_email: str, message: str, n_type: str = "alert") -> dict:
    try:
        themes = {
            "alert": {"color": "#2e7d32", "icon": "🌿", "title": "Smart Garden Alert"},
            "info": {"color": "#1565c0", "icon": "ℹ️", "title": "Garden Update"},
        }

        theme = themes.get(n_type, themes["alert"])

        html = f"""
        <html>
        <body style="font-family:Arial;background:#f5f5f5;padding:20px;">
            <div style="max-width:420px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;">
                <div style="background:{theme['color']};color:white;padding:20px;text-align:center;">
                    <div style="font-size:24px;">{theme['icon']}</div>
                    <div style="font-size:18px;">{theme['title']}</div>
                </div>
                <div style="padding:20px;font-size:14px;">
                    {message}
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEText(html, "html")
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = f"{theme['icon']} {theme['title']}"

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return {"ok": True, "channel": "email"}

    except Exception as e:
        logger.exception("Email failed")
        return {"ok": False, "channel": "email", "error": str(e)}


# =========================================================
# 🔔 FIREBASE PUSH
# =========================================================

def send_firebase_push(token: str, title: str, body: str) -> dict:
    try:
        headers = {
            "Authorization": f"key={FIREBASE_SERVER_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body
            }
        }

        r = requests.post(FCM_URL, json=payload, headers=headers, timeout=10)

        return {
            "ok": r.status_code == 200,
            "channel": "firebase",
            "error": None if r.status_code == 200 else r.text
        }

    except Exception as e:
        logger.exception("Firebase push failed")
        return {"ok": False, "channel": "firebase", "error": str(e)}


# =========================================================
# 🤖 DISCORD (BOT QUEUE)
# =========================================================

def queue_discord_message(discord_user_id: str, message: str) -> dict:
    try:
        r = requests.post(
            DISCORD_QUEUE_URL,
            json={
                "discord_user_id": str(discord_user_id),
                "message": message
            },
            timeout=5
        )

        return {
            "ok": r.ok,
            "channel": "discord",
            "status_code": r.status_code,
            "error": None if r.ok else r.text
        }

    except Exception as e:
        logger.exception("Discord queue failed")
        return {"ok": False, "channel": "discord", "error": str(e)}


# =========================================================
# 🌿 MAIN NOTIFICATION ENGINE
# =========================================================
def send_notification(user_id: int, message: str, db, n_type: str = "alert") -> dict:
    try:
        contact = (
            db.query(UserContact)
            .filter(UserContact.user_id == user_id)
            .first()
        )

        if not contact:
            logger.warning(f"No contact found for user {user_id}")
            return {"ok": False, "error": "No contact found"}

        results = []

        # =====================================================
        # 🤖 DISCORD (clean queue system)
        # =====================================================
        discord_id = getattr(contact, "discord_user_id", None)

        print("🧠 Discord ID:", discord_id)

        if discord_id:
            discord_result = queue_discord_message(discord_id, message)
            print("DISCORD RESULT:", discord_result)
            results.append(discord_result)
        else:
            results.append({
                "ok": False,
                "channel": "discord",
                "error": "missing discord_user_id"
            })

        # =====================================================
        # 📧 EMAIL
        # =====================================================
        user = db.query(User).filter(User.id == user_id).first()

        if user and user.email:
            results.append(send_email(user.email, message, n_type=n_type))
        else:
            results.append({
                "ok": False,
                "channel": "email",
                "error": "missing email"
            })

        # =====================================================
        # 🔥 FIREBASE
        # =====================================================
        firebase_token = getattr(contact, "firebase_token", None)

        if firebase_token:
            results.append(
                send_firebase_push(
                    firebase_token,
                    "🌿 Smart Garden",
                    message
                )
            )
        else:
            results.append({
                "ok": False,
                "channel": "firebase",
                "error": "missing token"
            })

        # =====================================================
        # 🧠 FINAL RESULT
        # =====================================================
        return {
            "ok": any(r.get("ok") for r in results),
            "results": results
        }

    except Exception as e:
        logger.exception("Notification system failed")
        return {"ok": False, "error": str(e)}
    try:
        contact = (
            db.query(UserContact)
            .filter(UserContact.user_id == user_id)
            .first()
        )

        if not contact:
            logger.warning(f"No contact found for user {user_id}")
            return {"ok": False, "error": "No contact found"}

        results = []

        # =====================================================
        # 🤖 DISCORD (via bot queue)
        # =====================================================
        if getattr(contact, "discord_user_id", None):
            try:
                r = requests.post(
                    "http://127.0.0.1:8000/api/bot/queue",
                    json={
                        "discord_user_id": str(contact.discord_user_id),
                        "message": message
                    },
                    timeout=5
                )
                print("DISCORD STATUS:", r.status_code)
                print("DISCORD RESPONSE:", r.text)
                results.append({
                    "ok": r.status_code == 200,
                    "channel": "discord"
                })
            except Exception as e:
                results.append({"ok": False, "error": str(e), "channel": "discord"})

        # =====================================================
        # 📧 EMAIL
        # =====================================================
        user = db.query(User).filter(User.id == user_id).first()

        if user and user.email:
            results.append(send_email(user.email, message, n_type=n_type))

        # =====================================================
        # 🔥 FIREBASE
        # =====================================================
        if getattr(contact, "firebase_token", None):
            results.append(
                send_firebase_push(
                    contact.firebase_token,
                    "🌿 Smart Garden",
                    message
                )
            )

        return {
            "ok": any(r.get("ok") for r in results),
            "results": results
        }

    except Exception as e:
        logger.exception("Notification system failed")
        return {"ok": False, "error": str(e)}
# =========================================================
# 🌿 HELPERS
# =========================================================

def should_alert(user_id: int, bed_id: str, alert_type: str, new_state: str) -> bool:
    key = (user_id, bed_id, alert_type)

    if _last_state.get(key) == new_state:
        return False

    _last_state[key] = new_state
    return True


def get_bed_owner(db, bed_id: str):
    meta = (
        db.query(BedMetaDB)
        .filter(BedMetaDB.bed_id == bed_id)
        .first()
    )
    return meta.user_id if meta else None


# =========================================================
# 🌿 FORMATTER
# =========================================================

def format_garden_email(project_name: str, message: str) -> str:
    return f"""
🌿 Smart Garden Alert
Project: {project_name}

{message}
"""
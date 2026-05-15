import smtplib
import logging
import os
import requests

from email.mime.text import MIMEText
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

from carriers import Carrier
from models import BedMetaDB, User, UserContact
from dotenv import load_dotenv
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
# 🌿 ROUTER (decision layer)
# =========================================================

class NotificationRouter:
    def __init__(self, db):
        self.db = db

    def handle(self, event: GardenEvent):

        key = (event.user_id, event.bed_id, event.type)
        now = datetime.utcnow()

        last = _last_alert_time.get(key)

        # -----------------------------
        # cooldown logic
        # -----------------------------
        if event.level == EventLevel.CRITICAL:
            cooldown = timedelta(minutes=1)
        elif event.level == EventLevel.WARNING:
            cooldown = timedelta(minutes=5)
        else:
            cooldown = timedelta(minutes=2)

        if last and (now - last) < cooldown:
            return

        # -----------------------------
        # route event
        # -----------------------------
        if event.level == EventLevel.INFO:
            return

        send_notification(
            user_id=event.user_id,
            message=event.message,
            db=self.db,
            n_type="alert" if event.level == EventLevel.CRITICAL else "info"
        )

        _last_alert_time[key] = now


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
        return {"ok": False, "error": str(e), "channel": "email"}


# =========================================================
# 📡 DISCORD
# =========================================================

def send_discord(webhook_url: str, message: str) -> dict:
    try:
        r = requests.post(webhook_url, json={"content": message}, timeout=10)

        if r.status_code == 204:
            return {"ok": True, "channel": "discord"}

        return {"ok": False, "error": r.text, "channel": "discord"}

    except Exception as e:
        return {"ok": False, "error": str(e), "channel": "discord"}


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

        if r.status_code == 200:
            return {"ok": True, "channel": "firebase"}

        logger.warning(f"Firebase failed: {r.text}")
        return {"ok": False, "error": r.text, "channel": "firebase"}

    except Exception as e:
        logger.exception("Firebase push failed")
        return {"ok": False, "error": str(e), "channel": "firebase"}


# =========================================================
# 🌿 DELIVERY LAYER
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

        # -----------------------------
        # DISCORD
        # -----------------------------
        if getattr(contact, "discord_webhook", None):
            results.append(send_discord(contact.discord_webhook, message))

        # -----------------------------
        # EMAIL
        # -----------------------------
        user = db.query(User).filter(User.id == user_id).first()

        if user and user.email:
            results.append(send_email(user.email, message, n_type=n_type))

        # -----------------------------
        # FIREBASE
        # -----------------------------
        if getattr(contact, "firebase_token", None):
            results.append(
                send_firebase_push(
                    contact.firebase_token,
                    "🌿 Smart Garden",
                    message
                )
            )

        # -----------------------------
        # FIXED SUCCESS LOGIC
        # -----------------------------
        success = any(r.get("ok") for r in results)

        if not results:
            success = False

        return {
            "ok": success,
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

    last = _last_state.get(key)
    if last == new_state:
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
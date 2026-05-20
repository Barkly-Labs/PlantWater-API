import smtplib
import logging
import os
import requests
import json

from email.mime.text import MIMEText
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

from dotenv import load_dotenv
from models import BedMetaDB, User, UserContact

import google.auth.transport.requests
import google.oauth2.service_account
import os

load_dotenv()

# =========================================================
# 🌿 CONFIG
# =========================================================

logger = logging.getLogger("notifications")

SENDER_EMAIL = os.getenv("GARDEN_EMAIL")
SENDER_PASSWORD = os.getenv("GARDEN_PASSWORD")

FCM_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FCM_SERVICE_ACCOUNT = os.path.join(
    BASE_DIR,
    "config",
    "smart-garden-4d476-firebase-adminsdk-fbsvc-ca34395065.json"
)

FCM_URL = f"https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send"

DISCORD_QUEUE_URL = "http://127.0.0.1:8000/api/bot/queue"

SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


# =========================================================
# 🌱 STATE
# =========================================================

_last_state = {}
_last_alert_time: Dict[tuple, datetime] = {}


# =========================================================
# 🌿 EVENTS
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
# 🔐 FIREBASE AUTH
# =========================================================

def _firebase_token():
    creds = google.oauth2.service_account.Credentials.from_service_account_file(
        FCM_SERVICE_ACCOUNT,
        scopes=SCOPES,
    )

    request = google.auth.transport.requests.Request()
    creds.refresh(request)

    return creds.token


# =========================================================
# 📧 EMAIL
# =========================================================

def send_email(to_email: str, message: str, n_type: str = "alert") -> dict:
    try:
        subject = "🌿 Smart Garden Alert"

        html = f"""
        <html>
        <body style="font-family:Arial;background:#f5f5f5;padding:20px;">
            <div style="max-width:420px;margin:auto;background:white;padding:20px;border-radius:12px;">
                <h3 style="margin:0 0 10px 0;">🌿 Smart Garden</h3>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """

        msg = MIMEText(html, "html")
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return {"ok": True, "channel": "email"}

    except Exception as e:
        logger.exception("Email failed")
        return {"ok": False, "channel": "email", "error": str(e)}


# =========================================================
# 🤖 DISCORD
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
        logger.exception("Discord failed")
        return {"ok": False, "channel": "discord", "error": str(e)}


# =========================================================
# 🔥 FIREBASE PUSH (FIXED)
# =========================================================

def send_firebase_push(token: str, title: str, body: str, data: dict = None) -> dict:
    try:
        access_token = _firebase_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body
                },
                "data": {k: str(v) for k, v in (data or {}).items()},
                "android": {
                    "priority": "high"
                },
                "apns": {
                    "headers": {
                        "apns-priority": "10"
                    }
                }
            }
        }

        r = requests.post(
            FCM_URL,
            headers=headers,
            json=payload   # ✅ FIXED (this is critical)
        )

        print("FCM STATUS:", r.status_code)
        print("FCM RESPONSE:", r.text)

        return {
            "ok": r.status_code == 200,
            "channel": "firebase",
            "error": None if r.status_code == 200 else r.text
        }

    except Exception as e:
        logger.exception("Firebase failed")
        return {"ok": False, "channel": "firebase", "error": str(e)}


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
            return {"ok": False, "error": "No contact found"}

        results = []

        # =====================================================
        # 🤖 DISCORD
        # =====================================================
        if getattr(contact, "discord_user_id", None):
            results.append(queue_discord_message(contact.discord_user_id, message))
        else:
            results.append({"ok": False, "channel": "discord", "error": "missing discord id"})

        # =====================================================
        # 📧 EMAIL
        # =====================================================
        user = db.query(User).filter(User.id == user_id).first()

        if user and user.email:
            results.append(send_email(user.email, message, n_type))
        else:
            results.append({"ok": False, "channel": "email", "error": "missing email"})

        # =====================================================
        # 🔥 FIREBASE
        # =====================================================
        if getattr(contact, "firebase_token", None):
            results.append(
                send_firebase_push(
                    contact.firebase_token,
                    "🌿 Smart Garden",
                    message,
                    data={
                        "type": "garden_alert",
                        "severity": n_type
                    }
                )
            )
        else:
            results.append({"ok": False, "channel": "firebase", "error": "missing token"})

        return {
            "ok": any(r.get("ok") for r in results),
            "results": results
        }

    except Exception as e:
        logger.exception("Notification engine failed")
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


def test_firebase(db):
    contact = db.query(UserContact).first()

    return send_firebase_push(
        contact.firebase_token,
        "Test",
        "Firebase is working",
        {"test": "true"}
    )
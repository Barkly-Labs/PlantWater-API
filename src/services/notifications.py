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

        data_dict = {k: str(v) for k, v in (data or {}).items()}

        payload = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body
                },
                "data": data_dict,
                "webpush": {
                    "headers": {
                        "TTL": "86400"
                    },
                    "data": data_dict,
                    "notification": {
                        "title": title,
                        "body": body,
                        "icon": "/static/icon.png",
                        "badge": "/static/icon.png"
                    }
                },
                "android": {
                    "priority": "high",
                    "notification": {
                        "title": title,
                        "body": body,
                        "click_action": "FLUTTER_NOTIFICATION_CLICK"
                    }
                },
                "apns": {
                    "headers": {
                        "apns-priority": "10"
                    },
                    "payload": {
                        "aps": {
                            "alert": {
                                "title": title,
                                "body": body
                            },
                            "sound": "default",
                            "badge": 1
                        }
                    }
                }
            }
        }

        r = requests.post(
            FCM_URL,
            headers=headers,
            json=payload
        )

        logger.info(f"FCM SEND TO {token[:20]}... | Status: {r.status_code}")
        
        if r.status_code != 200:
            logger.error(f"FCM ERROR for token {token[:20]}... | Response: {r.text}")
            
            # Parse error to detect invalid tokens
            try:
                error_data = r.json()
                error_msg = str(error_data)
                
                if "INVALID_ARGUMENT" in error_msg or "REGISTRATION_TOKEN_NOT_REGISTERED" in error_msg:
                    return {
                        "ok": False,
                        "channel": "firebase",
                        "error": "INVALID_TOKEN",
                        "status_code": r.status_code
                    }
            except:
                pass
            
            return {
                "ok": False,
                "channel": "firebase",
                "error": r.text,
                "status_code": r.status_code
            }

        try:
            response_data = r.json()
            message_id = response_data.get("name", "unknown")
            logger.info(f"FCM SUCCESS | MessageID: {message_id} | Token: {token[:20]}...")
        except:
            logger.info(f"FCM SUCCESS | Token: {token[:20]}...")

        return {
            "ok": True,
            "channel": "firebase",
            "error": None,
            "status_code": 200
        }

    except Exception as e:
        logger.exception(f"Firebase push failed for token {token[:20]}...")
        return {"ok": False, "channel": "firebase", "error": str(e), "status_code": 0}


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
        # 🔥 FIREBASE (MULTI-DEVICE WITH VALIDATION)
        # =====================================================
        
        firebase_tokens = getattr(contact, "firebase_tokens", None)
        
        if firebase_tokens and isinstance(firebase_tokens, list) and len(firebase_tokens) > 0:
            logger.info(f"FIREBASE: Sending to {len(firebase_tokens)} token(s) for user {user_id}")
            
            invalid_tokens = []
            
            for idx, token in enumerate(firebase_tokens):
                if not token or not isinstance(token, str):
                    logger.warning(f"Skipping invalid token at index {idx}: {token}")
                    invalid_tokens.append(idx)
                    continue

                logger.info(f"Sending Firebase message {idx+1}/{len(firebase_tokens)}: {token[:20]}...")
                
                result = send_firebase_push(
                    token,
                    "🌿 Smart Garden",
                    message,
                    data={
                        "type": "garden_alert",
                        "severity": n_type
                    }
                )
                
                # Mark invalid tokens for removal
                if not result.get("ok") and result.get("error") == "INVALID_TOKEN":
                    logger.warning(f"Token invalid/expired, marking for removal: {token[:20]}...")
                    invalid_tokens.append(idx)
                
                results.append(result)
            
            # CLEANUP: Remove invalid tokens from database
            if invalid_tokens:
                logger.info(f"Cleaning up {len(invalid_tokens)} invalid token(s)")
                remaining_tokens = [
                    t for i, t in enumerate(firebase_tokens) 
                    if i not in invalid_tokens
                ]
                contact.firebase_tokens = remaining_tokens
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(contact, "firebase_tokens")
                try:
                    db.commit()
                    logger.info(f"Cleaned tokens. Remaining: {len(remaining_tokens)}")
                except Exception as e:
                    logger.error(f"Failed to clean tokens: {e}")
                    db.rollback()
        else:
            logger.warning(f"No Firebase tokens for user {user_id}")
            results.append({
                "ok": False,
                "channel": "firebase",
                "error": "no firebase tokens registered"
            })
        
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
    
    if not contact or not contact.firebase_tokens:
        return {"ok": False, "error": "No firebase tokens found"}
    
    token = contact.firebase_tokens[0]
    return send_firebase_push(
        token,
        "Test",
        "Firebase is working",
        {"test": "true"}
    )
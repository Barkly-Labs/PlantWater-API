"""
Notification Services
Email-to-SMS gateway (Gmail SMTP fallback)
Future-ready for Twilio upgrade
"""

import smtplib
from email.mime.text import MIMEText

from models import UserContact


# -----------------------------
# Carrier gateway mapping
# -----------------------------
CARRIERS = {
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "att": "txt.att.net",
    "mint": "tmomail.net",
    "rogers": "pcs.rogers.com",
    "sprint": "messaging.sprintpcs.com"
}


# -----------------------------
# SMTP CONFIG (Gmail)
# -----------------------------
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = "xSeveredgamerx@gmail.com"
SENDER_PASSWORD = "klxm qlal bsya ehcl"  # MUST be Gmail App Password


def send_sms_alert(phone: str, carrier: str, message: str):
    try:
        if carrier not in CARRIERS:
            return {
                "ok": False,
                "error": f"Invalid carrier: {carrier}"
            }

        to_email = f"{phone}@{CARRIERS[carrier]}"

        msg = MIMEText(message)
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = ""

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return {
            "ok": True,
            "to": to_email
        }

    except Exception as e:
        return {
            "ok": False,
            "error": repr(e)
        }


# -----------------------------
# HIGH LEVEL: send alert to user
# -----------------------------
def send_alert(user_id: int, message: str, db) -> bool:
    try:
        contact = (
            db.query(UserContact)
            .filter(UserContact.user_id == user_id)
            .first()
        )

        if not contact:
            print("❌ No contact found for user:", user_id)
            return False

        if not contact.phone or not contact.carrier:
            print("❌ Missing phone/carrier for user:", user_id)
            return False

        return send_sms_alert(
            phone=contact.phone,
            carrier=contact.carrier,
            message=message
        )

    except Exception as e:
        print("❌ send_alert ERROR:", repr(e))
        return False
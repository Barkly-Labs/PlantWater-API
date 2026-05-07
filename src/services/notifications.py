import smtplib
import logging
from email.mime.text import MIMEText
from carriers import Carrier
from models import User, UserContact

logger = logging.getLogger("notifications")

CARRIERS = {
    Carrier.verizon: "vtext.com",
    Carrier.tmobile: "tmomail.net",
    Carrier.att: "txt.att.net",
    Carrier.mint: "tmomail.net",
    Carrier.rogers: "pcs.rogers.com",
    Carrier.sprint: "messaging.sprintpcs.com",
}
SENDER_EMAIL="xseveredgamerx@gmail.com"
SENDER_PASSWORD="bdxo qthd qtao fvrd"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587

def send_email(to_email: str, message: str) -> dict:
    try:
        msg = MIMEText(message)
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = "Smart Garden Alert"

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return {"ok": True, "channel": "email"}

    except Exception as e:
        logger.exception("Email send failed")
        return {"ok": False, "error": str(e), "channel": "email"}


# -----------------------------
# CHANNEL: DISCORD (optional but recommended)
# -----------------------------
def send_discord(webhook_url: str, message: str) -> dict:
    try:
        import requests

        payload = {"content": message}
        r = requests.post(webhook_url, json=payload, timeout=10)

        if r.status_code == 204:
            return {"ok": True, "channel": "discord"}

        return {"ok": False, "error": r.text, "channel": "discord"}

    except Exception as e:
        return {"ok": False, "error": str(e), "channel": "discord"}


# -----------------------------
# MAIN NOTIFICATION HUB
# -----------------------------
def send_notification(user_id: int, message: str, db) -> dict:
    """
    Unified notification system:
    - tries Discord first (if available)
    - falls back to email
    - SMS support removed (optional later via Twilio)
    """

    try:
        contact = (
            db.query(UserContact)
            .filter(UserContact.user_id == user_id)
            .first()
        )

        if not contact:
            return {"ok": False, "error": "No contact found"}

        results = []

        # -----------------------------
        # DISCORD (preferred channel)
        # -----------------------------
        if hasattr(contact, "discord_webhook") and contact.discord_webhook:
            results.append(
                send_discord(contact.discord_webhook, message)
            )

        # -----------------------------
        # EMAIL fallback (FIXED)
        # -----------------------------
        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        email = user.email if user else None

        if email:
            results.append(
                send_email(email, message)
            )
        # -----------------------------
        # Evaluate results
        # -----------------------------
        success = any(r.get("ok") for r in results)

        return {
            "ok": success,
            "results": results
        }

    except Exception as e:
        logger.exception("Notification system failed")
        return {"ok": False, "error": str(e)}
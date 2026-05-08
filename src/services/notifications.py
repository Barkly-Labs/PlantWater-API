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


def send_email(
    to_email: str,
    message: str,
    project_name: str = "SMART GARDEN",
    n_type: str = "alert"
) -> dict:
    try:
        plant = "🌿"

        # -----------------------------
        # THEME COLORS BY TYPE
        # -----------------------------
        themes = {
            "alert": {
                "color": "#2e7d32",
                "bg": "#f5f7f6",
                "icon": "🌿",
                "title": "Smart Garden Alert"
            },
            "error": {
                "color": "#c62828",
                "bg": "#fff5f5",
                "icon": "🚨",
                "title": "System Error"
            },
            "info": {
                "color": "#1565c0",
                "bg": "#f5f9ff",
                "icon": "ℹ️",
                "title": "System Update"
            }
        }

        theme = themes.get(n_type, themes["alert"])

        html = f"""
        <html>
        <body style="margin:0; padding:0; background:{theme['bg']}; font-family:Arial, sans-serif;">

            <div style="
                max-width:420px;
                margin:40px auto;
                background:#ffffff;
                border-radius:16px;
                overflow:hidden;
                box-shadow:0 8px 24px rgba(0,0,0,0.08);
                border:1px solid #e6e6e6;
            ">

                <!-- HEADER -->
                <div style="
                    background:{theme['color']};
                    padding:22px;
                    text-align:center;
                    color:white;
                ">
                    <div style="font-size:28px;">{theme['icon']}</div>
                    <div style="font-size:18px; font-weight:600; margin-top:6px;">
                        {theme['title']}
                    </div>
                    <div style="font-size:12px; opacity:0.9; margin-top:4px;">
                        {project_name}
                    </div>
                </div>

                <!-- BODY -->
                <div style="padding:20px;">

                    <div style="font-size:13px; color:#777; margin-bottom:10px;">
                        Notification Type: {n_type.upper()}
                    </div>

                    <div style="
                        font-size:15px;
                        color:#222;
                        line-height:1.5;
                        background:#f7faf7;
                        padding:14px;
                        border-radius:10px;
                        border:1px solid #e8eee8;
                    ">
                        {message}
                    </div>

                    <div style="
                        margin-top:18px;
                        font-size:11px;
                        color:#999;
                        text-align:center;
                    ">
                        Sent from Smart Garden System
                    </div>

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

        return {
            "ok": True,
            "channel": "email",
            "type": n_type,
            "to": to_email
        }

    except Exception as e:
        logger.exception("Email send failed")
        return {
            "ok": False,
            "error": str(e),
            "channel": "email",
            "type": n_type
        }
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
def send_notification(user_id: int, message: str, db, n_type: str = "alert") -> dict:
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

        print(f"DEBUG: Sending notification to user_id={user_id} via email={email}")

        if email:
            results.append(
                send_email(email, message, n_type=n_type)
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
    


def format_garden_email(project_name: str, message: str) -> str:
    plant = "🌿"

    border = "+" + "-" * 50 + "+"

    body = f"""
{border}
| {plant} Smart Garden Alert
| Project: {project_name}
|
| {message}
{border}
"""

    return body
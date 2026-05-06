"""
Notification Services
Email-to-SMS gateway and alert management (placeholder for future Twilio integration)
"""
import smtplib
from email.mime.text import MIMEText
import os
from db import Session
from models import User


def send_sms_alert(phone: str, carrier: str, message: str) -> bool:
    """
    Send SMS alert via email-to-SMS gateway.
    """

    carriers = {
        "verizon": "vtext.com",
        "tmobile": "tmomail.net",
        "att": "txt.att.net",
        "mint": "tmomail.net",
        "rogers": "pcs.rogers.com",
        "sprint": "messaging.sprintpcs.com"
    }

    domain = carriers.get(carrier)
    if not domain:
        return False

    try:
        # clean phone (remove spaces, +, etc)
        phone = "".join(filter(str.isdigit, phone))

        to_email = f"{phone}@{domain}"

        msg = MIMEText(message)
        msg["Subject"] = ""  # SMS ignores subject
        msg["From"] = os.getenv("SMTP_EMAIL")
        msg["To"] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(
            os.getenv("SMTP_EMAIL"),
            os.getenv("SMTP_PASSWORD")  # ⚠️ app password
        )

        server.sendmail(
            os.getenv("SMTP_EMAIL"),
            to_email,
            msg.as_string()
        )

        server.quit()

        return True

    except Exception as e:
        print("SMS ERROR:", e)
        return False
    

def send_alert(user_id: int, message: str, db=None) -> bool:
    """
    Send alert to user based on their notification settings.
    """

    if db is None:
        print("No DB session provided")
        return False

    try:
        contact = db.query(User).filter(
            User.user_id == user_id
        ).first()

        if not contact:
            return False

        if not contact.phone or not contact.carrier:
            return False

        return send_sms_alert(
            phone=contact.phone,
            carrier=contact.carrier,
            message=message
        )

    except Exception as e:
        print("ALERT ERROR:", e)
        return False
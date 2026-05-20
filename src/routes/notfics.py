from fastapi import APIRouter, Depends, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from db import get_db
from models import UserContact, User
from schemas import DeviceTokenRegister
from auth import get_current_user
from services.notifications import send_notification

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


# ============================================================
# TEST NOTIFICATION (DEV TOOL)
# ============================================================
@router.post("/test")
def test_notification(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Send a test message to the currently authenticated user.
    Body: { "message": str }
    """

    message = payload.get("message", "Test alert from system")

    return send_notification(user.id, message, db)


# ============================================================
# SEND INFO
# ============================================================
@router.post("/send/info")
def send_info(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    message = payload.get("message")

    if not message:
        return {"ok": False, "error": "Missing message"}

    return send_notification(user.id, message, db, n_type="info")


# ============================================================
# SEND ERROR
# ============================================================
@router.post("/send/error")
def send_error(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    message = payload.get("message")

    if not message:
        return {"ok": False, "error": "Missing message"}

    return send_notification(user.id, message, db, n_type="error")


# ============================================================
# SEND ALERT
# ============================================================
@router.post("/send/alert")
def send_alert(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    message = payload.get("message")

    if not message:
        return {"ok": False, "error": "Missing message"}

    return send_notification(user.id, message, db, n_type="alert")


# ============================================================
# GET USER CONTACT (DEBUG TOOL)
# ============================================================
@router.get("/contact")
def get_contact(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Debug endpoint to verify stored contact info for logged-in user.
    """

    contact = (
        db.query(UserContact)
        .filter(UserContact.user_id == user.id)
        .first()
    )

    if not contact:
        return {"ok": False, "error": "No contact found"}

    return {
        "ok": True,
        "user_id": contact.user_id,
        "phone": contact.phone,
        "email": getattr(contact, "email", None),
        "discord_webhook": getattr(contact, "discord_webhook", None),
        "firebase_tokens": getattr(contact, "firebase_tokens", []),
    }


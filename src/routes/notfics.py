from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models import UserContact
from schemas import DeviceTokenRegister
from auth import get_current_user
from services.notifications import send_notification
router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


# -----------------------------
# TEST NOTIFICATION (dev tool)
# -----------------------------
@router.post("/test",tags=["Notifications"])
def test_notification(payload: dict, db: Session = Depends(get_db)):
    """
    Send a test message to a user_id.
    Body: { "user_id": int, "message": str }
    """

    user_id = payload.get("user_id")
    message = payload.get("message", "Test alert from system")

    return send_notification(user_id, message, db)


# -----------------------------
# SEND ALERT (main system trigger)
# -----------------------------
@router.post("/send/info",tags=["Notifications"])
def send_alert(
    payload: dict,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    message = payload.get("message")

    if not message:
        return {"ok": False, "error": "Missing message"}

    return send_notification(user.id, message, db, n_type="info")


@router.post("/send/error",tags=["Notifications"])
def send_alert(
    payload: dict,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    message = payload.get("message")

    if not message:
        return {"ok": False, "error": "Missing message"}

    return send_notification(user.id, message, db, n_type="error")



@router.post("/send/alert")
def send_alert(
    payload: dict,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    message = payload.get("message")

    if not message:
        return {"ok": False, "error": "Missing message"}

    return send_notification(user.id, message, db, n_type="alert")




# -----------------------------
# GET USER CONTACT (debug tool)
# -----------------------------
@router.get("/contact/{user_id}",tags=["Notifications"])
def get_contact(user_id: int, db: Session = Depends(get_db)):
    """
    Debug endpoint to verify stored contact info.
    """

    contact = (
        db.query(UserContact)
        .filter(UserContact.user_id == user_id)
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
    }

@router.post("/notifications/register-device",tags=["Notifications"])
def register_device_token(data: DeviceTokenRegister, db: Session):

    contact = (
        db.query(UserContact)
        .filter(UserContact.user_id == data.user_id)
        .first()
    )

    # -----------------------------
    # create contact if missing
    # -----------------------------
    if not contact:
        contact = UserContact(
            user_id=data.user_id,
            firebase_token=data.firebase_token
        )
        db.add(contact)

    # -----------------------------
    # update token
    # -----------------------------
    else:
        contact.firebase_token = data.firebase_token

    db.commit()

    return {
        "ok": True,
        "message": "Device token registered"
    }

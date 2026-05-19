







from fastapi import APIRouter, Depends, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from db import get_db
from models import UserContact, User
from schemas import DeviceTokenRegister
from auth import get_current_user
from services.notifications import send_notification

router = APIRouter(prefix="/api/firebase", tags=["firebase"])



# ============================================================
# REGISTER DEVICE (FIXED AUTH MODEL)
# ============================================================
@router.post("/register-device", tags=["firebase"])
def register_device_token(
    data: DeviceTokenRegister,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
    
):
    """
    Registers or updates Firebase device token for authenticated user.
    """

    # -----------------------------------------------------
    # Find existing contact (assumes 1:1 user -> contact)
    # -----------------------------------------------------
    contact = (
        db.query(UserContact)
        .filter(UserContact.user_id == user.id)
        .one_or_none()
    )

    # -----------------------------------------------------
    # Create if missing
    # -----------------------------------------------------
    if not contact:
        contact = UserContact(
            user_id=user.id,
            firebase_token=data.firebase_token,
            # optional future-safe fields
            # last_token_update=datetime.utcnow()
        )
        db.add(contact)

    # -----------------------------------------------------
    # Update if changed (avoid pointless DB writes)
    # -----------------------------------------------------
    else:
        if contact.firebase_token != data.firebase_token:
            contact.firebase_token = data.firebase_token
            # contact.last_token_update = datetime.utcnow()

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            "ok": False,
            "error": f"DB commit failed: {str(e)}"
        }

    return {
        "ok": True,
        "message": "Device token registered"
    }
from pathlib import Path
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent
SW_FILE = (BASE_DIR / "../static/firebase-messaging-sw.js").resolve()

@router.get("/firebase-messaging-sw.js",tags=["firebase"])
def firebase_sw():
    return FileResponse(
        path=str(SW_FILE),
        media_type="application/javascript"
    )

@router.post("/firebase-token")
def save_firebase_token(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token = data.get("firebase_token")

    if not token:
        return {"ok": False, "error": "No token"}

    contact = (
        db.query(UserContact)
        .filter(UserContact.user_id == user.id)
        .first()
    )

    if not contact:
        contact = UserContact(user_id=user.id)
        db.add(contact)

    contact.firebase_token = token

    db.commit()

    return {"ok": True}








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
    Registers Firebase device token (multi-device safe).
    """

    contact = (
        db.query(UserContact)
        .filter(UserContact.user_id == user.id)
        .one_or_none()
    )

    if not contact:
        contact = UserContact(
            user_id=user.id,
            firebase_tokens=[]
        )
        db.add(contact)

    # ensure list exists
    if contact.firebase_tokens is None:
        contact.firebase_tokens = []

    # avoid duplicates
    if data.firebase_token not in contact.firebase_tokens:
        contact.firebase_tokens.append(data.firebase_token)

    try:
        db.commit()
        db.refresh(contact)
    except Exception as e:
        db.rollback()
        return {
            "ok": False,
            "error": f"DB commit failed: {str(e)}"
        }

    return {
        "ok": True,
        "firebase_tokens": contact.firebase_tokens
    }
@router.delete("/firebase-token")
def delete_firebase_token(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    token = data.get("firebase_token")

    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact or not contact.firebase_tokens:
        return {"ok": True}

    contact.firebase_tokens = [
        t for t in contact.firebase_tokens if t != token
    ]

    db.commit()

    return {
        "ok": True,
        "firebase_tokens": contact.firebase_tokens
    }
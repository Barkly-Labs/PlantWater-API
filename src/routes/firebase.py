






from fastapi import APIRouter, Depends, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import event
from sqlalchemy.orm.attributes import flag_modified

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
        flag_modified(contact, "firebase_tokens")

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

@router.post("/firebase-token")
def save_firebase_token(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token = data.get("firebase_token")

    if not token:
        return {"ok": False, "error": "No token"}

    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact:
        contact = UserContact(
            user_id=user.id,
            firebase_tokens=[]
        )
        db.add(contact)

    # =========================
    # MULTI DEVICE FIX (SAFE)
    # =========================
    if contact.firebase_tokens is None:
        contact.firebase_tokens = []

    if token not in contact.firebase_tokens:
        contact.firebase_tokens.append(token)
        flag_modified(contact, "firebase_tokens")

    db.commit()
    db.refresh(contact)

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
    flag_modified(contact, "firebase_tokens")

    db.commit()

    return {
        "ok": True,
        "firebase_tokens": contact.firebase_tokens
    }
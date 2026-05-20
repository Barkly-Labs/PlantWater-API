






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
    import logging
    logger = logging.getLogger("firebase")
    
    token = data.get("firebase_token")

    if not token:
        logger.warning(f"User {user.id}: No token provided")
        return {"ok": False, "error": "No token"}

    logger.info(f"User {user.id}: Registering firebase token {token[:30]}...")
    
    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact:
        logger.info(f"User {user.id}: Creating new UserContact")
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
        logger.info(f"User {user.id}: Token added. Total tokens: {len(contact.firebase_tokens)}")
    else:
        logger.info(f"User {user.id}: Token already registered")

    logger.info(f"User {user.id}: Tokens to save: {[t[:20]+'...' for t in contact.firebase_tokens]}")
    
    try:
        db.commit()
        db.refresh(contact)
        logger.info(f"User {user.id}: Successfully saved. DB confirmed {len(contact.firebase_tokens)} token(s)")
    except Exception as e:
        logger.error(f"User {user.id}: DB commit failed: {e}")
        db.rollback()
        return {"ok": False, "error": f"DB error: {str(e)}"}

    return {
        "ok": True,
        "firebase_tokens": contact.firebase_tokens,
        "count": len(contact.firebase_tokens)
    }
@router.delete("/firebase-token")
def disable_firebase(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact:
        return {"ok": True}

    contact.firebase_tokens = []

    flag_modified(contact, "firebase_tokens")
    db.commit()

    return {"ok": True}
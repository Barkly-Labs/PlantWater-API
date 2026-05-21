






from fastapi import APIRouter, Depends, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import event
from sqlalchemy.orm.attributes import flag_modified

from db import get_db
from models import UserContact, User
from schemas import DeviceTokenRegister, DeviceTokenRemove
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
    data: DeviceTokenRemove,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Removes a specific Firebase token for multi-device support.
    If no token specified in body, removes all tokens (backward compatibility).
    """
    import logging
    logger = logging.getLogger("firebase")
    
    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact:
        return {"ok": True}

    token_to_remove = data.firebase_token

    # Backward compatibility: if no token specified, remove all
    if not token_to_remove:
        logger.info(f"User {user.id}: Removing ALL tokens (backward compat)")
        contact.firebase_tokens = []
    else:
        # Remove only the specified token (new behavior for multi-device)
        if contact.firebase_tokens and token_to_remove in contact.firebase_tokens:
            contact.firebase_tokens.remove(token_to_remove)
            logger.info(f"User {user.id}: Removed token {token_to_remove[:20]}... | Remaining: {len(contact.firebase_tokens)}")
        else:
            logger.warning(f"User {user.id}: Token {token_to_remove[:20]}... not found")
            return {"ok": False, "error": "Token not found"}

    flag_modified(contact, "firebase_tokens")
    try:
        db.commit()
        db.refresh(contact)
        logger.info(f"User {user.id}: DB committed. Tokens remaining: {len(contact.firebase_tokens or [])}")
    except Exception as e:
        logger.error(f"User {user.id}: DB commit failed: {e}")
        db.rollback()
        return {"ok": False, "error": f"DB error: {str(e)}"}

    return {
        "ok": True,
        "firebase_tokens": contact.firebase_tokens,
        "count": len(contact.firebase_tokens or [])
    }
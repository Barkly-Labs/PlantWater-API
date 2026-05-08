"""
User & Authentication Routes
Registration, login, user contact/notification management
"""

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from db import get_db
from models import DiscordAccount, User, UserContact
from schemas import RegisterRequest, LoginRequest, ContactRequest
from auth import get_current_user
from services.notifications import send_notification

router = APIRouter()


# ============================================================
# AUTH ENDPOINTS
# ============================================================

@router.post("/api/register", tags=["Auth"])
def register(data: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Register new user account."""
    from fastapi import HTTPException
    
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=data.email,
        password=data.password
    )

    db.add(user)
    db.commit()
    db.refresh(user)


    send_notification(user.id, "Created New Account with the email "+user.email, db, n_type="alert")

    response.set_cookie(
        key="user_id",
        value=str(user.id),
        httponly=True,
        samesite="lax",
        path="/"
    )

    return {"ok": True, "user_id": user.id}


@router.post("/api/login", tags=["Auth"])
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login with email and password."""
    from fastapi import HTTPException
    
    user = db.query(User).filter(User.email == data.email).first()

    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response.set_cookie(
        key="user_id",
        value=str(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/"
    )

    return {"ok": True}


@router.get("/logout", tags=["Auth"])
def logout():
    """Logout user by clearing cookies."""
    response = RedirectResponse(url="/login")

    response.delete_cookie("user_id", path="/")
    response.delete_cookie("token", path="/")

    return response


# ============================================================
# USER CONTACT & NOTIFICATION ENDPOINTS
# ============================================================

@router.post("/api/user/contact", tags=["SMS"])
def save_user_contact(
    data: ContactRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Save user contact information for SMS alerts."""
    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact:
        contact = UserContact(user_id=user.id)
        db.add(contact)

    contact.phone = data.phone
    contact.carrier = data.carrier

    db.commit()
    db.refresh(contact)

    return {
        "ok": True,
        "phone": contact.phone,
        "carrier": contact.carrier
    }


@router.get("/api/carriers", tags=["SMS"])
def get_carriers():
    """Get available SMS carriers."""
    return {
        "verizon": {
            "sms": "vtext.com",
            "label": "Verizon"
        },
        "tmobile": {
            "sms": "tmomail.net",
            "label": "T-Mobile"
        },
        "att": {
            "sms": "txt.att.net",
            "label": "AT&T"
        },
        "mint": {
            "sms": "tmomail.net",
            "label": "Mint Mobile"
        },
        "rogers": {
            "sms": "pcs.rogers.com",
            "label": "Rogers (CA)"
        },
        "sprint": {
            "sms": "messaging.sprintpcs.com",
            "label": "Sprint"
        }
    }

@router.get("/api/user/notifications", tags=["SMS"])
def get_notifications(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    discord = db.query(DiscordAccount).filter(
        DiscordAccount.user_id == user.id
    ).first()

    return {
        "phone": contact.phone if contact else None,
        "carrier": contact.carrier if contact else None,

        # 👇 THIS is what your UI is missing
        "discord_user_id": discord.discord_user_id if discord else None,
        "discord_username": discord.discord_username if discord else None,
    }

@router.post("/api/user/notifications", tags=["SMS"])
def update_notifications(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact:
        contact = UserContact(user_id=user.id)
        db.add(contact)

    # SMS
    contact.phone = data.get("phone")
    contact.carrier = data.get("carrier")

    # DISCORD (NEW)
    contact.discord_user_id = data.get("discord_user_id", contact.discord_user_id)
    contact.discord_username = data.get("discord_username", contact.discord_username)
    contact.discord_access_token = data.get("discord_access_token", contact.discord_access_token)

    db.commit()
    db.refresh(contact)

    return {"ok": True}
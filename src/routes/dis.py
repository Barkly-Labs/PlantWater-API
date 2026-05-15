import os
from dotenv import load_dotenv
import requests
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from db import get_db
from models import User, DiscordAccount, UserContact
from auth import get_current_user

router = APIRouter()

# =========================================================
# 🌿 CONFIG
# =========================================================
load_dotenv()
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SYSTEM_BASE_URL = os.getenv("SYSTEM_BASE_URL")

REDIRECT_URI = "http://127.0.0.1:8000/api/discord/callback"
DISCORD_API = "https://discord.com/api/v10"


# =========================================================
# 🌿 STEP 1: CONNECT DISCORD (redirect user)
# =========================================================

@router.get("/api/discord/connect", tags=["Discord"])
def discord_connect():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "identify"
    }

    url = "https://discord.com/oauth2/authorize?" + urlencode(params)
    return RedirectResponse(url)


# =========================================================
# 🌿 STEP 2: OAUTH CALLBACK (link account)
# =========================================================

@router.get("/api/discord/callback", tags=["Discord"])
def discord_callback(
    request: Request,
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # 1. exchange code for access token
    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10
    )

    if not token_res.ok:
        raise HTTPException(status_code=400, detail="Discord auth failed")

    access_token = token_res.json()["access_token"]

    # 2. fetch discord user
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )

    discord_data = user_res.json()
    discord_id = discord_data["id"]
    discord_username = discord_data["username"]

    # =====================================================
    # 🌿 STORE IN DiscordAccount (auth table)
    # =====================================================
    link = db.query(DiscordAccount).filter(
        DiscordAccount.user_id == user.id
    ).first()

    if not link:
        link = DiscordAccount(
            user_id=user.id,
            discord_user_id=discord_id,
            discord_username=discord_username
        )
        db.add(link)
    else:
        link.discord_user_id = discord_id
        link.discord_username = discord_username

    # =====================================================
    # 🌿 STORE IN UserContact (notifications FIX)
    # =====================================================
    contact = db.query(UserContact).filter(
        UserContact.user_id == user.id
    ).first()

    if not contact:
        contact = UserContact(user_id=user.id)

    contact.discord_user_id = discord_id

    db.add(contact)

    db.commit()
    
    return RedirectResponse(
    url= SYSTEM_BASE_URL+"/notifications?discord=connected"
)

# =========================================================
# 🌿 STEP 3: GET MY DISCORD STATUS (SECURE)
# =========================================================

@router.get("/api/discord/me", tags=["Discord"])
def get_my_discord(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    link = db.query(DiscordAccount).filter(
        DiscordAccount.user_id == user.id
    ).first()

    if not link:
        return {"connected": False}

    return {
        "connected": True,
        "discord_user_id": link.discord_user_id,
        "discord_username": link.discord_username
    }


# =========================================================
# 🌿 STEP 4: DISCONNECT DISCORD
# =========================================================

@router.delete("/api/discord/disconnect", tags=["Discord"])
def disconnect_discord(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    link = db.query(DiscordAccount).filter(
        DiscordAccount.user_id == user.id
    ).first()

    if link:
        db.delete(link)
        db.commit()

    return {"ok": True}


# =========================================================
# 🌿 STEP 5: SEND TEST DM (DEBUG ONLY)
# =========================================================

def send_discord_dm(discord_user_id: str, message: str) -> dict:
    try:
        headers = {
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json"
        }

        # create DM channel
        r = requests.post(
            f"{DISCORD_API}/users/@me/channels",
            headers=headers,
            json={"recipient_id": discord_user_id},
            timeout=10
        )

        if not r.ok:
            return {"ok": False, "error": r.text}

        channel_id = r.json()["id"]

        # send message
        r = requests.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers=headers,
            json={"content": message},
            timeout=10
        )

        if r.ok:
            return {"ok": True}

        return {"ok": False, "error": r.text}

    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/discord/test", tags=["Discord"])
def test_discord_dm(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    link = db.query(DiscordAccount).filter(
        DiscordAccount.user_id == user.id
    ).first()

    if not link:
        return {"ok": False, "error": "Discord not connected"}

    return send_discord_dm(link.discord_user_id, payload.get("message", "test"))

@router.get("/api/discord/users", tags=["Discord"])
def get_discord_users(db: Session = Depends(get_db)):
    users = db.query(DiscordAccount).all()

    return [
        {
            "discord_user_id": u.discord_user_id,
            "user_id": u.user_id
        }
        for u in users
    ]

@router.post("/api/user/link-discord")
def link_discord(user_id: int, discord_user_id: str, db: Session = Depends(get_db)):
    contact = (
        db.query(UserContact)
        .filter(UserContact.user_id == user_id)
        .first()
    )

    if not contact:
        contact = UserContact(user_id=user_id)
        db.add(contact)

    contact.discord_user_id = discord_user_id

    db.commit()

    return {"ok": True}

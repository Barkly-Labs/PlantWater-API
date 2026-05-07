import requests
from fastapi import Depends
from sqlalchemy.orm import Session
from auth import get_current_user
from db import get_db
from models import User


from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from db import get_db
from models import User, BedMetaDB,DiscordAccount
from auth import get_current_user

router = APIRouter()

DISCORD_CLIENT_ID = "1494822521109872720"
DISCORD_CLIENT_SECRET = "Gm2n_IU_bXUvORUTCYeR1MrkNVX5hA4B"
REDIRECT_URI = "http://127.0.0.1:8000/api/discord/callback"


@router.get("/api/discord/callback")
def discord_callback(
    request: Request,
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)  # 👈 IMPORTANT
):
    # =========================
    # 1. Exchange code for token
    # =========================
    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if not token_res.ok:
        return RedirectResponse("/notifications?discord=error")

    token_data = token_res.json()
    access_token = token_data["access_token"]

    # =========================
    # 2. Get Discord user
    # =========================
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    discord_user = user_res.json()

    discord_id = discord_user["id"]
    discord_name = discord_user["username"]

    # =========================
    # 3. SAVE TO DB (THIS WAS MISSING)
    # =========================
    contact = db.query().filter(
        DiscordAccount.user_id == user.id
    ).first()

    if not contact:
        contact = DiscordAccount(user_id=user.id)
        db.add(contact)

    contact.discord_user_id = discord_id
    contact.discord_username = discord_name

    db.commit()

    return RedirectResponse("/notifications?discord=connected")

from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import os


REDIRECT_URI = "http://127.0.0.1:8000/api/discord/callback"


@router.get("/api/discord/connect", tags=["Discord"])
def discord_connect():

    params = {
        "client_id": DISCORD_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "identify"
    }

    discord_url = (
        "https://discord.com/oauth2/authorize?"
        + urlencode(params)
    )

    return RedirectResponse(discord_url)
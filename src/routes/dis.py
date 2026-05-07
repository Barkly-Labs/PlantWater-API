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
from models import User, BedMetaDB
from auth import get_current_user

router = APIRouter()

DISCORD_CLIENT_ID = "YOUR_ID"
DISCORD_CLIENT_SECRET = "YOUR_SECRET"
REDIRECT_URI = "http://127.0.0.1:8000/api/discord/callback"


@router.get("/api/discord/callback")
def discord_callback(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)  # user already logged into your app
):

    # 1. exchange code for token
    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": 1494822521109872720,
            "client_secret": "Gm2n_IU_bXUvORUTCYeR1MrkNVX5hA4B",
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    ).json()

    access_token = token_res.get("access_token")

    # 2. fetch discord user
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    discord_id = user_res["id"]
    discord_username = user_res["username"]

    # 3. save to your DB
    user.discord_user_id = discord_id
    user.discord_username = discord_username
    user.discord_connected = True

    db.commit()

    return {"ok": True, "discord_connected": True}



from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import os

DISCORD_CLIENT_ID = 1494822521109872720

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
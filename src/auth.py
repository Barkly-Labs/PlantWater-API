"""
Authentication & Authorization
Cookie-based authentication using user_id
"""

import hashlib
import secrets
import jwt

from fastapi import Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session

from db import get_db
from models import APIKey, User

# ============================================================
# CONFIG
# ============================================================

SECRET_KEY = "your_secret_key_here"  # replace with a secure random key in production
ALGORITHM = "HS256"

# ============================================================
# JWT UTILITIES (kept for future use, now fixed)
# ============================================================

def decode_token(token: str):
    """Decode JWT token safely"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


# ============================================================
# CURRENT USER (COOKIE AUTH - FIXED & CLEANED)
# ============================================================

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Cookie-based authentication.

    Reads user_id from cookie and validates against DB.
    """

    user_id = request.cookies.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user_id format")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user


# ============================================================
# API KEY UTILITIES (FIXED MINOR SAFETY EDGE CASES)
# ============================================================

def generate_raw_key():
    return secrets.token_hex(32)


def hash_key(raw_key: str):
    return hashlib.sha256(raw_key.encode()).hexdigest()


def verify_api_key(
    x_api_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    API key validation via SHA256 hash lookup
    """

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    key_hash = hash_key(x_api_key)

    key = (
        db.query(APIKey)
        .filter(
            APIKey.key_hash == key_hash,
            APIKey.active == True
        )
        .first()
    )

    if not key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return key
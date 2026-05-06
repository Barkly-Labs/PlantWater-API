"""
Authentication & Authorization
Cookie-based user authentication using user_id
"""

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db import get_db
from models import User

# ============================================================
# JWT CONFIGURATION
# ============================================================
SECRET_KEY = "your-secret"
ALGORITHM = "HS256"


# ============================================================
# TOKEN UTILITIES
# ============================================================
def decode_token(token: str):
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.DecodeError:
        return None


# ============================================================
# CURRENT USER DEPENDENCY
# ============================================================
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Dependency to get the current authenticated user from cookie.

    Reads user_id from the "user_id" cookie and verifies the user exists.
    Raises 401 if not authenticated or user not found.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User: The authenticated User object

    Raises:
        HTTPException: 401 if not authenticated or invalid session
    """
    user_id = request.cookies.get("user_id")

    print("COOKIES:", request.cookies)
    print("USER_ID:", user_id)

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id = int(user_id)
    except:
        raise HTTPException(status_code=401, detail="Invalid user_id")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user

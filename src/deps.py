from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from db import get_db
from models import User  # adjust if needed

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user
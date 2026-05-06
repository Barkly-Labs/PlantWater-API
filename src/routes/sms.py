from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from models import User
from services.notifications import send_alert



router = APIRouter()


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from services.notifications import send_alert
from auth import get_current_user  # IMPORTANT: NOT from db

router = APIRouter()


@router.post("/api/notifications/test-sms", tags=["SMS"])
def test_sms(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = send_alert(
        user_id=user.id,
        message="🌿 Test message from your garden system",
        db=db
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="SMS failed (check logs / contact info / SMTP)"
        )

    return {
        "ok": True,
        "message": "Test SMS attempted",
        "debug": result
    }


@router.get("/api/notifications/debug/{user_id}", tags=["SMS"])
def debug_user_contact(user_id: int, db: Session = Depends(get_db)):
    contact = db.query(User).filter(User.id == user_id).first()
    return {
        "exists": bool(contact),
        "phone": getattr(contact, "phone", None),
        "carrier": getattr(contact, "carrier", None)
    }
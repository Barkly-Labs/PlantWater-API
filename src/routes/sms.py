from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from deps import get_current_user
from services.notifications import send_alert

router = APIRouter()


@router.post("/api/notifications/test")
def test_sms(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = send_alert(
        user_id=user.id,
        message="🌿 Test message from your garden system",
        db=db
    )

    return {
        "ok": success,
        "message": "SMS sent" if success else "Failed to send SMS"
    }
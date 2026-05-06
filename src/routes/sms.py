
from fastapi import APIRouter

from models import BedReading, BedMetaDB, BedConfigDB, User
from schemas import BedData, BedConfig

router = APIRouter()

@router.post("/api/notifications/test")
def test_sms(user=Depends(get_current_user), db: Session = Depends(get_db)):

    success = send_alert(
        user_id=user.id,
        message="🌿 Test message from your garden system",
        db=db
    )

    return {"ok": success}
# api/bot_bridge.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/bot", tags=["Bot"])

class Msg(BaseModel):
    discord_user_id: str
    message: str

BOX = []

@router.post("/queue")
def add_message(msg: Msg):
    BOX.append(msg)
    return {"ok": True}


@router.get("/poll")
def get_messages():
    global BOX
    msgs = BOX
    BOX = []
    return msgs
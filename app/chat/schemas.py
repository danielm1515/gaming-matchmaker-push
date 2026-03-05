import uuid
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import MessageType


class SenderMini(BaseModel):
    id: uuid.UUID
    username: str
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: uuid.UUID
    party_id: uuid.UUID
    sender: SenderMini | None = None
    content: str
    type: MessageType
    sent_at: datetime

    class Config:
        from_attributes = True

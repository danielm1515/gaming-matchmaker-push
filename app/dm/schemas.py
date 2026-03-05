import uuid
from datetime import datetime
from pydantic import BaseModel


class PlayerMini(BaseModel):
    id: uuid.UUID
    username: str
    avatar_url: str | None

    model_config = {"from_attributes": True}


class DMResponse(BaseModel):
    id: uuid.UUID
    sender: PlayerMini
    receiver_id: uuid.UUID
    content: str
    is_read: bool
    sent_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    partner: PlayerMini
    last_message: str
    last_sent_at: datetime
    unread_count: int

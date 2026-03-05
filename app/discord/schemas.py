import uuid
from datetime import datetime
from pydantic import BaseModel


class DiscordChannelResponse(BaseModel):
    party_id: uuid.UUID
    text_channel_id: str
    voice_channel_id: str | None
    invite_url: str
    password: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

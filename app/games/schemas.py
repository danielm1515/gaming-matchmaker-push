import uuid
from pydantic import BaseModel


class GameResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    max_party_size: int
    is_active: bool

    class Config:
        from_attributes = True

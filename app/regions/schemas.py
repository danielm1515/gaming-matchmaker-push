import uuid
from pydantic import BaseModel


class RegionResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    countries: list[str]

    class Config:
        from_attributes = True

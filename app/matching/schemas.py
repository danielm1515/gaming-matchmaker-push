from pydantic import BaseModel
from app.parties.schemas import PartyResponse


class MatchResultResponse(BaseModel):
    party: PartyResponse
    match_score: int
    region_score: int
    skill_score: int
    fill_score: int
    availability_score: int

    class Config:
        from_attributes = True

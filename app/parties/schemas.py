import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.common.enums import SkillLevel, PartyStatus
from app.players.schemas import PlayerResponse
from app.games.schemas import GameResponse
from app.regions.schemas import RegionResponse


class PartyMemberResponse(BaseModel):
    player: PlayerResponse
    joined_at: datetime
    is_ready: bool

    class Config:
        from_attributes = True


class PartyResponse(BaseModel):
    id: uuid.UUID
    game: GameResponse
    region: RegionResponse
    leader: PlayerResponse
    members: list[PartyMemberResponse] = []
    name: str | None = None
    max_size: int
    min_skill: SkillLevel
    max_skill: SkillLevel
    status: PartyStatus
    is_public: bool
    created_at: datetime

    @property
    def current_size(self) -> int:
        return len(self.members)

    class Config:
        from_attributes = True


class PartyCreate(BaseModel):
    game_id: uuid.UUID
    region_id: uuid.UUID
    name: str | None = None
    max_size: int = 4
    min_skill: SkillLevel = SkillLevel.BRONZE
    max_skill: SkillLevel = SkillLevel.MASTER
    is_public: bool = True

    @field_validator("max_size")
    @classmethod
    def validate_max_size(cls, v: int) -> int:
        if not 2 <= v <= 6:
            raise ValueError("Party size must be between 2 and 6")
        return v


class PartyUpdate(BaseModel):
    name: str | None = None
    min_skill: SkillLevel | None = None
    max_skill: SkillLevel | None = None
    is_public: bool | None = None

import uuid
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import SkillLevel, AvailabilityStatus


class RegionMini(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    class Config:
        from_attributes = True


class GameMini(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None

    class Config:
        from_attributes = True


class PlayerGameResponse(BaseModel):
    game: GameMini
    skill_level: SkillLevel
    hours_played: int

    class Config:
        from_attributes = True


class PlayerResponse(BaseModel):
    id: uuid.UUID
    username: str
    avatar_url: str | None = None
    bio: str | None = None
    region: RegionMini | None = None
    country_code: str | None = None
    skill_level: SkillLevel
    availability: AvailabilityStatus
    games_played: int
    player_games: list[PlayerGameResponse] = []
    last_seen_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PlayerUpdate(BaseModel):
    username: str | None = None
    bio: str | None = None
    country_code: str | None = None
    skill_level: SkillLevel | None = None
    availability: AvailabilityStatus | None = None
    avatar_url: str | None = None
    region_id: uuid.UUID | None = None


class AddGameRequest(BaseModel):
    game_id: uuid.UUID
    skill_level: SkillLevel = SkillLevel.SILVER
    hours_played: int = 0


class PlayerListParams(BaseModel):
    game_id: uuid.UUID | None = None
    region_code: str | None = None
    country_code: str | None = None
    skill_level: SkillLevel | None = None
    availability: AvailabilityStatus | None = None
    limit: int = 20
    offset: int = 0

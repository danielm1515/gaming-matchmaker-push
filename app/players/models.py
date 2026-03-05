import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.common.enums import SkillLevel, AvailabilityStatus


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    skill_level: Mapped[SkillLevel] = mapped_column(
        SAEnum(SkillLevel), nullable=False, default=SkillLevel.SILVER
    )
    availability: Mapped[AvailabilityStatus] = mapped_column(
        SAEnum(AvailabilityStatus), nullable=False, default=AvailabilityStatus.ONLINE, index=True
    )
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    region: Mapped["Region"] = relationship("Region", back_populates="players")
    player_games: Mapped[list["PlayerGame"]] = relationship(
        "PlayerGame", back_populates="player", cascade="all, delete-orphan"
    )
    led_parties: Mapped[list["Party"]] = relationship("Party", back_populates="leader")
    party_memberships: Mapped[list["PartyMember"]] = relationship(
        "PartyMember", back_populates="player", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender")


class PlayerGame(Base):
    __tablename__ = "player_games"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    skill_level: Mapped[SkillLevel] = mapped_column(
        SAEnum(SkillLevel), nullable=False, default=SkillLevel.SILVER
    )
    hours_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="player_games")
    game: Mapped["Game"] = relationship("Game", back_populates="player_games")

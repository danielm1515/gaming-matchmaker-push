import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.common.enums import SkillLevel, PartyStatus


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id"), nullable=False, index=True
    )
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False, index=True
    )
    leader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_size: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    min_skill: Mapped[SkillLevel] = mapped_column(
        SAEnum(SkillLevel), nullable=False, default=SkillLevel.BRONZE
    )
    max_skill: Mapped[SkillLevel] = mapped_column(
        SAEnum(SkillLevel), nullable=False, default=SkillLevel.MASTER
    )
    status: Mapped[PartyStatus] = mapped_column(
        SAEnum(PartyStatus), nullable=False, default=PartyStatus.OPEN, index=True
    )
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="parties")
    region: Mapped["Region"] = relationship("Region", back_populates="parties")
    leader: Mapped["Player"] = relationship("Player", back_populates="led_parties")
    members: Mapped[list["PartyMember"]] = relationship(
        "PartyMember", back_populates="party", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="party", cascade="all, delete-orphan"
    )

    @property
    def current_size(self) -> int:
        return len(self.members)


class PartyMember(Base):
    __tablename__ = "party_members"

    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parties.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    party: Mapped["Party"] = relationship("Party", back_populates="members")
    player: Mapped["Player"] = relationship("Player", back_populates="party_memberships")

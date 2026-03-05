import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class PartyDiscordChannel(Base):
    __tablename__ = "party_discord_channels"

    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parties.id", ondelete="CASCADE"), primary_key=True
    )
    text_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    voice_channel_id: Mapped[str] = mapped_column(String(32), nullable=True)
    invite_url: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

import uuid
from sqlalchemy import String, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    countries: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Relationships
    players: Mapped[list["Player"]] = relationship("Player", back_populates="region")
    parties: Mapped[list["Party"]] = relationship("Party", back_populates="region")

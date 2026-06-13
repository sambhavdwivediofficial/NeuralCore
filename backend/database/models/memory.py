# database/models/memory.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.agent import Agent

class MemoryLayer(str, enum.Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    SESSION = "session"


class Memory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_memories"
    __table_args__ = (
        Index("ix_agent_memories_agent_layer", "agent_id", "layer"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    layer: Mapped[MemoryLayer] = mapped_column(Enum(MemoryLayer, name="memory_layer", native_enum=False), nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped["Agent"] = relationship(back_populates="memories")
# database/models/agent.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin
from settings import AgentType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.memory import Memory
    from database.models.project import Project

class AgentStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Agent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agents"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType, name="agent_type", native_enum=False), nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status", native_enum=False), default=AgentStatus.CREATED, nullable=False
    )
    model_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), default="neuralcore-48b", nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_iterations: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    tools: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="agents")
    memories: Mapped[list["Memory"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
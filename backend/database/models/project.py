# database/models/project.py
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.agent import Agent
    from database.models.dataset import Dataset
    from database.models.knowledgebase import KnowledgeBase
    from database.models.user import User
    from database.models.workflow import Workflow

class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    owner: Mapped["User | None"] = relationship(back_populates="projects")
    agents: Mapped[list["Agent"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="project", cascade="all, delete-orphan")


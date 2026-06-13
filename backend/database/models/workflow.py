# database/models/workflow.py
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.project import Project

class WorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Workflow(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflows"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status", native_enum=False), default=WorkflowStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="workflows")
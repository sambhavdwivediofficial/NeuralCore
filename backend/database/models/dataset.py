# database/models/dataset.py
from __future__ import annotations

import enum
import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.project import Project

class DatasetFormat(str, enum.Enum):
    ALPACA = "alpaca"
    SHAREGPT = "sharegpt"
    OPENAI = "openai"
    CUSTOM = "custom"


class DatasetStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Dataset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "datasets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[DatasetFormat] = mapped_column(
        Enum(DatasetFormat, name="dataset_format", native_enum=False), default=DatasetFormat.ALPACA, nullable=False
    )
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status", native_enum=False), default=DatasetStatus.PENDING, nullable=False
    )
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    num_examples: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    validation_report: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="datasets")
# database/models/knowledgebase.py
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

class ChunkingStrategy(str, enum.Enum):
    TOKEN = "token"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    MARKDOWN = "markdown"
    CODE = "code"
    AST = "ast"
    HYBRID = "hybrid"
    CHARACTER = "character"


class KnowledgeBaseStatus(str, enum.Enum):
    CREATING = "creating"
    READY = "ready"
    INDEXING = "indexing"
    ERROR = "error"


class KnowledgeBase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_bases"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    vector_db_backend: Mapped[str] = mapped_column(String(50), default="qdrant", nullable=False)
    collection_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(50), default="openai", nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    chunking_strategy: Mapped[ChunkingStrategy] = mapped_column(
        Enum(ChunkingStrategy, name="chunking_strategy", native_enum=False),
        default=ChunkingStrategy.RECURSIVE,
        nullable=False,
    )
    chunk_size: Mapped[int] = mapped_column(Integer, default=512, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[KnowledgeBaseStatus] = mapped_column(
        Enum(KnowledgeBaseStatus, name="knowledgebase_status", native_enum=False),
        default=KnowledgeBaseStatus.CREATING,
        nullable=False,
    )
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="knowledge_bases")
# backend/database/models/knowledgebase.py
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from database.base import Base, TimestampMixin, UUIDMixin

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


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    REPROCESSING = "reprocessing"


class KnowledgeBase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_bases"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    documents: Mapped[list["Document"]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="upload", nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", native_enum=False),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chunks"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="chunks")
    document: Mapped["Document"] = relationship(back_populates="chunks")
    
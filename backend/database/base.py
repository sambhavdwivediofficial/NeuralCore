# database/base.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy import DateTime, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)


ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: uuid.UUID) -> ModelType | None:
        result = await self.session.execute(select(self.model).where(self.model.id == id_))
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: Any = None,
        **filters: Any,
    ) -> list[ModelType]:
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def create(self, **kwargs: Any) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, id_: uuid.UUID, **kwargs: Any) -> ModelType | None:
        instance = await self.get_by_id(id_)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, id_: uuid.UUID) -> bool:
        instance = await self.get_by_id(id_)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def exists(self, **filters: Any) -> bool:
        stmt = select(self.model.id)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None
# database/repositories/project_repository.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from database.base import BaseRepository
from database.models.project import Project


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_by_slug(self, slug: str) -> Project | None:
        result = await self.session.execute(select(Project).where(Project.slug == slug))
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.organization_id == organization_id, Project.is_active.is_(True))
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Project]:
        result = await self.session.execute(select(Project).where(Project.owner_id == owner_id))
        return list(result.scalars().all())

    async def slug_exists(self, slug: str) -> bool:
        result = await self.session.execute(select(Project.id).where(Project.slug == slug))
        return result.scalar_one_or_none() is not None
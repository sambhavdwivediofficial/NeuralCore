# database/connection.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from settings import Settings
from database.base import Base
from database.models import agent, dataset, knowledgebase, memory, project, user, workflow
from multitenancy.organizations import members, organization

_REGISTERED_MODELS = (
    agent.Agent,
    dataset.Dataset,
    knowledgebase.KnowledgeBase,
    memory.Memory,
    organization.Organization,
    members.OrganizationMember,
    project.Project,
    user.User,
    workflow.Workflow,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


def init_engine(settings: Settings) -> AsyncEngine:
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.database.echo,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=settings.database.pool_recycle,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine has not been initialized")
    return _engine


def get_session_factory() -> async_sessionmaker:
    if _session_factory is None:
        raise RuntimeError("Session factory has not been initialized")
    return _session_factory


async def dispose_engine(engine: AsyncEngine | None = None) -> None:
    target = engine or _engine
    if target is not None:
        await target.dispose()


async def create_all() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
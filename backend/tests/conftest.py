# tests/conftest.py
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models.agent import Agent, AgentStatus
from database.models.knowledgebase import ChunkingStrategy, KnowledgeBase, KnowledgeBaseStatus
from database.models.project import Project
from database.models.user import User
from multitenancy.organizations.members import MemberStatus, OrganizationMember
from multitenancy.organizations.organization import Organization, OrganizationPlan, OrganizationStatus
from settings import AgentType, Role, Settings, get_settings

_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    settings = get_settings()
    settings.environment = settings.environment.__class__.TESTING if hasattr(settings.environment.__class__, "TESTING") else settings.environment
    settings.debug = True
    return settings


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(_TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession) -> Organization:
    organization = Organization(
        name="Test Organization",
        slug=f"test-org-{uuid.uuid4().hex[:8]}",
        plan=OrganizationPlan.PROFESSIONAL,
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(organization)
    await db_session.flush()
    return organization


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_organization: Organization) -> User:
    from auth.password import hash_password
    from settings import get_settings as _get_settings

    user = User(
        organization_id=test_organization.id,
        email=f"test-{uuid.uuid4().hex[:8]}@neuralcore.test",
        hashed_password=hash_password("TestPassword123!", _get_settings()),
        full_name="Test User",
        role=Role.OWNER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    member = OrganizationMember(
        organization_id=test_organization.id,
        user_id=user.id,
        role=Role.OWNER,
        status=MemberStatus.ACTIVE,
    )
    db_session.add(member)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_organization: Organization, test_user: User) -> Project:
    project = Project(
        organization_id=test_organization.id,
        owner_id=test_user.id,
        name="Test Project",
        slug=f"test-project-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def test_knowledge_base(db_session: AsyncSession, test_project: Project) -> KnowledgeBase:
    kb = KnowledgeBase(
        project_id=test_project.id,
        name="Test Knowledge Base",
        collection_name=f"nc_test_{uuid.uuid4().hex[:12]}",
        embedding_provider="sentence_transformers",
        embedding_model="all-MiniLM-L6-v2",
        embedding_dimension=384,
        chunking_strategy=ChunkingStrategy.RECURSIVE,
        chunk_size=256,
        chunk_overlap=25,
        status=KnowledgeBaseStatus.READY,
    )
    db_session.add(kb)
    await db_session.flush()
    return kb


@pytest_asyncio.fixture
async def test_agent(db_session: AsyncSession, test_project: Project) -> Agent:
    agent = Agent(
        project_id=test_project.id,
        name="Test Agent",
        agent_type=AgentType.EXECUTOR,
        status=AgentStatus.CREATED,
        model_provider="local",
        model_name="neuralcore-48b",
        max_iterations=5,
    )
    db_session.add(agent)
    await db_session.flush()
    return agent


@pytest_asyncio.fixture
async def fake_redis():
    try:
        from fakeredis.aioredis import FakeRedis
    except ImportError:
        pytest.skip("fakeredis not installed; run: pip install fakeredis")
    client = FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession, fake_redis, test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    from app import create_app
    from api.dependencies import get_db, get_redis

    app = create_app()

    async def _override_get_db():
        yield db_session

    async def _override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(test_user: User, test_settings: Settings) -> dict[str, str]:
    from auth.jwt import create_access_token

    token = create_access_token(test_user, test_settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_text() -> str:
    return (
        "NeuralCore is an enterprise-grade AI infrastructure platform built for retrieval-augmented "
        "generation, agentic RAG, and multi-agent orchestration. It supports hybrid search combining "
        "vector similarity and BM25 keyword matching, fused using reciprocal rank fusion. The platform "
        "uses a Rust engine for performance-critical operations like HNSW indexing and tokenization."
    )


@pytest.fixture
def sample_documents() -> list[dict[str, Any]]:
    return [
        {"id": "doc1", "text": "NeuralCore uses hybrid retrieval combining vector and BM25 search.", "metadata": {"source": "docs"}},
        {"id": "doc2", "text": "Python is a high-level programming language used for AI development.", "metadata": {"source": "wiki"}},
        {"id": "doc3", "text": "The Rust engine provides fast vector similarity computation for NeuralCore.", "metadata": {"source": "docs"}},
    ]

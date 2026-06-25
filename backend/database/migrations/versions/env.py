# database/migrations/versions/env.py
from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from database.base import Base
from database.models.user import User
from database.models.project import Project
from database.models.agent import Agent
from database.models.knowledgebase import KnowledgeBase, Document, Chunk
from database.models.workflow import Workflow
from database.models.dataset import Dataset
from database.models.memory import Memory

try:
    from api.routes.project_members import ProjectMember
    from services.invite_service import OrganizationInvite
    from multitenancy.organizations.organization import Organization
    from multitenancy.organizations.members import OrganizationMember
except Exception:
    pass

target_metadata = Base.metadata

DB_URL = os.environ.get(
    "DATABASE__URL",
    "postgresql+psycopg2://neuralcore:dev-password-change-in-prod@postgres:5432/neuralcore"
).replace("+asyncpg", "+psycopg2")


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DB_URL
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

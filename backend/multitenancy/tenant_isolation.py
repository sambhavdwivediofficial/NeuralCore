# multitenancy/tenant_isolation.py
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from multitenancy.tenant_context import TenantContext


class TenantIsolationError(Exception):
    pass


def scope_to_tenant(stmt: Select, model: type, organization_id: uuid.UUID) -> Select:
    if not hasattr(model, "organization_id"):
        raise TenantIsolationError(f"{model.__name__} does not support tenant scoping")
    return stmt.where(model.organization_id == organization_id)


def assert_tenant_owns(resource_organization_id: uuid.UUID | None, tenant: TenantContext) -> None:
    if resource_organization_id is None or resource_organization_id != tenant.organization_id:
        raise TenantIsolationError("Resource does not belong to the current tenant")


@asynccontextmanager
async def rls_session(session: AsyncSession, organization_id: uuid.UUID) -> AsyncIterator[AsyncSession]:
    await session.execute(text("SET LOCAL app.current_tenant = :tenant_id"), {"tenant_id": str(organization_id)})
    try:
        yield session
    finally:
        await session.execute(text("RESET app.current_tenant"))


def tenant_cache_namespace(organization_id: uuid.UUID) -> str:
    return f"tenant:{organization_id}"


def tenant_storage_prefix(organization_id: uuid.UUID) -> str:
    return f"tenants/{organization_id}"
# dependencies.py
from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from settings import Settings, get_settings
from database.session import get_session
from database.models.user import User
from database.repositories.user_repository import UserRepository
from auth.jwt import decode_access_token
from auth.permissions import role_has_permission
from task_queue.redis import get_redis_client
from multitenancy.tenant_context import TenantContext
from multitenancy.tenant_resolver import resolve_tenant_context

bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings() -> Settings:
    return get_settings()


async def get_db(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncGenerator[AsyncSession, None]:
    yield session


async def get_redis(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AsyncGenerator[Redis, None]:
    client = get_redis_client(settings)
    try:
        yield client
    finally:
        pass


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = request.headers.get("x-request-id", "")
    return request_id


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials, settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(UUID(payload.sub))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    request_user = user
    request_user.token_payload = payload
    return request_user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: str):
    async def _dependency(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return user

    return _dependency


def require_permission(permission: str):
    async def _dependency(user: CurrentUser) -> User:
        if not role_has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return user

    return _dependency


async def get_tenant_context(
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantContext:
    return await resolve_tenant_context(request=request, user=user, db=db)


CurrentTenant = Annotated[TenantContext, Depends(get_tenant_context)]


class PaginationParams:
    def __init__(
        self,
        settings: Annotated[Settings, Depends(get_app_settings)],
        page: int = Query(1, ge=1),
        page_size: Optional[int] = Query(default=None, ge=1),
    ) -> None:
        max_page_size = settings.app.pagination.max_page_size
        default_page_size = settings.app.pagination.default_page_size
        size = page_size if page_size is not None else default_page_size
        self.page = page
        self.page_size = min(size, max_page_size)
        self.offset = (self.page - 1) * self.page_size
        self.limit = self.page_size


Pagination = Annotated[PaginationParams, Depends()]


class RateLimiter:
    def __init__(self, requests_per_minute: Optional[int] = None, burst: Optional[int] = None) -> None:
        self.requests_per_minute = requests_per_minute
        self.burst = burst

    async def __call__(
        self,
        request: Request,
        redis: Annotated[Redis, Depends(get_redis)],
        settings: Annotated[Settings, Depends(get_app_settings)],
    ) -> None:
        rate_settings = settings.app.rate_limit
        if not rate_settings.enabled:
            return
        limit = self.requests_per_minute or rate_settings.requests_per_minute
        burst = self.burst or rate_settings.burst
        identifier = request.headers.get("x-api-key") or (request.client.host if request.client else "anonymous")
        window = int(time.time() // 60)
        key = f"{rate_settings.key_prefix}:{identifier}:{window}"
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        if current > limit + burst:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )


default_rate_limiter = RateLimiter()


async def get_vector_store(
    tenant: CurrentTenant,
    settings: Annotated[Settings, Depends(get_app_settings)],
):
    from vector_stores import get_vector_store_adapter

    return get_vector_store_adapter(settings=settings, tenant=tenant)


async def get_embedding_provider(
    settings: Annotated[Settings, Depends(get_app_settings)],
    provider: Optional[str] = None,
):
    from embeddings.embedding_factory import get_embedding_provider as _get_embedding_provider

    return _get_embedding_provider(settings=settings, provider_name=provider)


async def get_model_gateway(
    settings: Annotated[Settings, Depends(get_app_settings)],
    provider: Optional[str] = None,
):
    from model_gateway.provider_factory import get_model_provider

    return get_model_provider(settings=settings, provider_name=provider)


async def get_memory_manager(
    tenant: CurrentTenant,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_app_settings)],
):
    from memory.memory_manager import MemoryManager

    return MemoryManager(tenant=tenant, db=db, redis=redis, settings=settings)


async def get_agent_orchestrator(
    tenant: CurrentTenant,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_app_settings)],
):
    from agents.orchestrator import AgentOrchestrator

    return AgentOrchestrator(tenant=tenant, db=db, redis=redis, settings=settings)

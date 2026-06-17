# api/dependencies.py
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from settings import Settings, get_settings
from collections.abc import AsyncGenerator

bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings() -> Settings:
    return get_settings()


async def get_db(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> AsyncGenerator[AsyncSession, None]:
    yield session


async def get_redis(
    settings: Annotated[Settings, Depends(get_app_settings)]
) -> AsyncGenerator[Redis, None]:
    from task_queue.redis import get_redis_client
    yield get_redis_client(settings)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    x_user_id: Optional[str] = Header(default=None),
):
    from auth.jwt import decode_access_token
    from database.models.user import User
    from database.repositories.user_repository import UserRepository

    token: str | None = None

    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        cookie_token = request.cookies.get("nc_access_token")
        if cookie_token:
            token = cookie_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token, settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(payload.sub))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    user.token_payload = payload
    return user


CurrentUser = Annotated[object, Depends(get_current_user)]


async def get_tenant_context(
    user: CurrentUser,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from multitenancy.tenant_resolver import resolve_tenant_context
    return await resolve_tenant_context(request=request, user=user, db=db)


CurrentTenant = Annotated[object, Depends(get_tenant_context)]


class PaginationParams:
    def __init__(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int | None = Query(None, ge=1),
    ) -> None:
        settings = get_settings()

        max_size = settings.app.pagination.max_page_size
        default_size = settings.app.pagination.default_page_size

        size = page_size if page_size is not None else default_size

        self.page = page
        self.page_size = min(size, max_size)
        self.offset = (self.page - 1) * self.page_size
        self.limit = self.page_size


Pagination = Annotated[PaginationParams, Depends()]


def require_roles(*roles: str):
    async def _dep(user: CurrentUser):
        from settings import Role
        if user.role.value not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return user
    return _dep


def require_permission(permission: str):
    async def _dep(user: CurrentUser):
        from auth.permissions import role_has_permission
        if not role_has_permission(user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")
        return user
    return _dep

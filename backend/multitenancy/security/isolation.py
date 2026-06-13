# multitenancy/security/isolation.py
from __future__ import annotations

import uuid
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from multitenancy.tenant_context import TenantContext

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class CrossTenantAccessError(Exception):
    def __init__(self, resource: str, organization_id: uuid.UUID | None, expected: uuid.UUID) -> None:
        self.resource = resource
        self.organization_id = organization_id
        self.expected = expected
        super().__init__(f"Cross-tenant access denied for {resource}")


def enforce_resource_tenant(
    resource_organization_id: uuid.UUID | None, tenant: TenantContext, resource: str = "resource"
) -> None:
    if resource_organization_id is None or resource_organization_id != tenant.organization_id:
        raise CrossTenantAccessError(resource, resource_organization_id, tenant.organization_id)


def tenant_scoped(resource_attr: str = "organization_id") -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tenant: TenantContext | None = kwargs.get("tenant")
            instance = kwargs.get("instance")
            if tenant is not None and instance is not None:
                resource_org_id = getattr(instance, resource_attr, None)
                enforce_resource_tenant(resource_org_id, tenant, type(instance).__name__)
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def sanitize_for_cross_tenant_log(value: str, tenant: TenantContext) -> str:
    return value.replace(str(tenant.organization_id), "***")
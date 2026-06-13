# multitenancy/tenant_router.py
from __future__ import annotations

import hashlib
import uuid

from multitenancy.organizations.organization import OrganizationPlan
from multitenancy.tenant_context import TenantContext
from settings import Settings, VectorDBBackend


class TenantResourceRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def vector_db_backend(self, tenant: TenantContext) -> VectorDBBackend:
        override = tenant.settings.get("vector_db_backend")
        if override:
            try:
                return VectorDBBackend(override)
            except ValueError:
                pass
        return self.settings.vector_db.default

    def collection_name(self, tenant: TenantContext, knowledge_base_id: uuid.UUID) -> str:
        return f"nc_{tenant.organization_id.hex}_{knowledge_base_id.hex}"

    def shared_collection_name(self, tenant: TenantContext) -> str:
        if tenant.plan == OrganizationPlan.ENTERPRISE:
            return f"nc_dedicated_{tenant.organization_id.hex}"
        shard_index = int(hashlib.sha256(str(tenant.organization_id).encode()).hexdigest(), 16) % 8
        return f"nc_shared_shard_{shard_index}"

    def storage_prefix(self, tenant: TenantContext) -> str:
        return f"organizations/{tenant.organization_id}"

    def cache_namespace(self, tenant: TenantContext) -> str:
        return f"tenant:{tenant.organization_id}"

    def queue_routing_key(self, tenant: TenantContext, task_name: str) -> str:
        if tenant.plan == OrganizationPlan.ENTERPRISE:
            return f"dedicated.{tenant.organization_id}.{task_name}"
        return f"shared.{task_name}"

    def model_gateway_provider(self, tenant: TenantContext) -> str:
        override = tenant.settings.get("default_llm_provider")
        if override:
            return override
        return self.settings.model_gateway.default_provider.value
# api/router.py
from __future__ import annotations

from fastapi import APIRouter

from api.routes import (
    admin,
    agents,
    analytics,
    auth,
    datasets,
    embeddings,
    ingestion,
    knowledgebases,
    memory,
    monitoring,
    organizations,
    pipelines,
    plugins,
    projects,
    prompts,
    reranking,
    retrieval,
    users,
    vectorstores,
    workflows,
    workspaces,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/auth", tags=["Users & Team"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(memory.router, prefix="/agents", tags=["Agent Memory"])
api_router.include_router(knowledgebases.router, prefix="/knowledge-bases", tags=["Knowledge Bases"])
api_router.include_router(ingestion.router, tags=["Ingestion"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["Embeddings"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["Retrieval"])
api_router.include_router(reranking.router, prefix="/reranking", tags=["Reranking"])
api_router.include_router(vectorstores.router, prefix="/vector-stores", tags=["Vector Stores"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["Prompts"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])
api_router.include_router(plugins.router, prefix="/plugins", tags=["Plugins"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

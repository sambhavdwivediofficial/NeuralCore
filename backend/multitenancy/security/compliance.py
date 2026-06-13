# multitenancy/security/compliance.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.agent import Agent
from database.models.dataset import Dataset
from database.models.knowledgebase import KnowledgeBase
from database.models.project import Project
from database.models.user import User
from database.models.workflow import Workflow
from multitenancy.organizations.organization import Organization, OrganizationPlan, OrganizationStatus

DATA_RETENTION_DAYS: dict[OrganizationPlan, int] = {
    OrganizationPlan.FREE: 30,
    OrganizationPlan.STARTER: 90,
    OrganizationPlan.PROFESSIONAL: 365,
    OrganizationPlan.ENTERPRISE: 1825,
}


def retention_cutoff(plan: OrganizationPlan) -> datetime:
    days = DATA_RETENTION_DAYS.get(plan, DATA_RETENTION_DAYS[OrganizationPlan.FREE])
    return datetime.now(timezone.utc) - timedelta(days=days)


async def export_organization_data(session: AsyncSession, organization_id: uuid.UUID) -> dict[str, Any]:
    organization_result = await session.execute(select(Organization).where(Organization.id == organization_id))
    organization = organization_result.scalar_one_or_none()
    if organization is None:
        raise ValueError("Organization not found")

    projects_result = await session.execute(select(Project).where(Project.organization_id == organization_id))
    projects = list(projects_result.scalars().all())
    project_ids = [project.id for project in projects]

    agents: list[Agent] = []
    datasets: list[Dataset] = []
    knowledge_bases: list[KnowledgeBase] = []
    workflows: list[Workflow] = []
    if project_ids:
        agents = list((await session.execute(select(Agent).where(Agent.project_id.in_(project_ids)))).scalars().all())
        datasets = list((await session.execute(select(Dataset).where(Dataset.project_id.in_(project_ids)))).scalars().all())
        knowledge_bases = list(
            (await session.execute(select(KnowledgeBase).where(KnowledgeBase.project_id.in_(project_ids)))).scalars().all()
        )
        workflows = list((await session.execute(select(Workflow).where(Workflow.project_id.in_(project_ids)))).scalars().all())

    return {
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
            "plan": organization.plan.value,
            "created_at": organization.created_at.isoformat(),
        },
        "projects": [{"id": str(p.id), "name": p.name, "slug": p.slug} for p in projects],
        "agents": [{"id": str(a.id), "name": a.name, "agent_type": a.agent_type.value} for a in agents],
        "datasets": [{"id": str(d.id), "name": d.name, "format": d.format.value} for d in datasets],
        "knowledge_bases": [{"id": str(k.id), "name": k.name} for k in knowledge_bases],
        "workflows": [{"id": str(w.id), "name": w.name} for w in workflows],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


async def anonymize_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    anon_id = uuid.uuid4().hex[:12]
    user.email = f"deleted-{anon_id}@neuralcore.invalid"
    user.full_name = "Deleted User"
    user.hashed_password = None
    user.is_active = False
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_recovery_codes = None
    user.oauth_provider = None
    user.oauth_subject = None
    user.bio = None
    user.metadata_ = {}
    await session.flush()
    return user


async def organizations_due_for_purge(session: AsyncSession) -> list[Organization]:
    result = await session.execute(select(Organization).where(Organization.status == OrganizationStatus.CANCELLED))
    organizations = list(result.scalars().all())
    due: list[Organization] = []
    now = datetime.now(timezone.utc)
    for organization in organizations:
        if organization.suspended_at is None:
            continue
        cutoff = organization.suspended_at + timedelta(days=DATA_RETENTION_DAYS.get(organization.plan, 30))
        if now >= cutoff:
            due.append(organization)
    return due
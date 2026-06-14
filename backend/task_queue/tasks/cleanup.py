# queue/tasks/cleanup.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from database.connection import get_session_factory
from database.models.memory import Memory
from database.models.user import User
from multitenancy.organizations.members import MemberStatus, OrganizationMember
from multitenancy.security.compliance import organizations_due_for_purge
from queue.celery import celery_app, run_async

logger = logging.getLogger(__name__)

INVITE_EXPIRY_DAYS = 7


@celery_app.task(
    name="queue.tasks.cleanup.purge_expired_memories",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def purge_expired_memories(self) -> int:
    return run_async(_purge_expired_memories())


async def _purge_expired_memories() -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            delete(Memory).where(Memory.expires_at.is_not(None), Memory.expires_at < now)
        )
        await session.commit()
        deleted = result.rowcount or 0
        logger.info("purged expired memories", extra={"count": deleted})
        return deleted


@celery_app.task(
    name="queue.tasks.cleanup.unlock_expired_accounts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def unlock_expired_accounts(self) -> int:
    return run_async(_unlock_expired_accounts())


async def _unlock_expired_accounts() -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(User).where(User.locked_until.is_not(None), User.locked_until < now)
        )
        users = list(result.scalars().all())
        for user in users:
            user.locked_until = None
            user.failed_login_attempts = 0
        await session.commit()
        logger.info("unlocked expired accounts", extra={"count": len(users)})
        return len(users)


@celery_app.task(
    name="queue.tasks.cleanup.cleanup_expired_invites",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def cleanup_expired_invites(self) -> int:
    return run_async(_cleanup_expired_invites())


async def _cleanup_expired_invites() -> int:
    session_factory = get_session_factory()
    cutoff = datetime.now(timezone.utc) - timedelta(days=INVITE_EXPIRY_DAYS)
    async with session_factory() as session:
        result = await session.execute(
            delete(OrganizationMember).where(
                OrganizationMember.status == MemberStatus.INVITED,
                OrganizationMember.invited_at.is_not(None),
                OrganizationMember.invited_at < cutoff,
            )
        )
        await session.commit()
        deleted = result.rowcount or 0
        logger.info("cleaned up expired invites", extra={"count": deleted})
        return deleted


@celery_app.task(
    name="queue.tasks.cleanup.purge_cancelled_organizations",
    bind=True,
    max_retries=3,
    default_retry_delay=600,
)
def purge_cancelled_organizations(self) -> int:
    return run_async(_purge_cancelled_organizations())


async def _purge_cancelled_organizations() -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        organizations = await organizations_due_for_purge(session)
        for organization in organizations:
            await session.execute(
                delete(OrganizationMember).where(OrganizationMember.organization_id == organization.id)
            )
            await session.delete(organization)
        await session.commit()
        logger.info("purged cancelled organizations", extra={"count": len(organizations)})
        return len(organizations)
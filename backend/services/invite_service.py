# backend/services/invite_service.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table, delete, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin, UUIDMixin
from database.models.user import User
from services.token_service import generate_invite_token, hash_invite_token, INVITE_EXPIRE_HOURS
from settings import Role


class OrganizationInvite(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organization_invites"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    invited_by_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role", native_enum=False), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


async def create_invite(
    db: AsyncSession,
    organization_id: uuid.UUID,
    invited_by_id: uuid.UUID,
    email: str,
    role: Role,
) -> str:
    raw_token = generate_invite_token()
    token_hash = hash_invite_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITE_EXPIRE_HOURS)

    await db.execute(
        delete(OrganizationInvite).where(
            OrganizationInvite.email == email,
            OrganizationInvite.organization_id == organization_id,
            OrganizationInvite.accepted_at == None,
        )
    )

    invite = OrganizationInvite(
        organization_id=organization_id,
        invited_by_id=invited_by_id,
        email=email,
        role=role,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()
    return raw_token


async def get_invite_by_token(
    db: AsyncSession, raw_token: str
) -> Optional[OrganizationInvite]:
    token_hash = hash_invite_token(raw_token)
    result = await db.execute(
        select(OrganizationInvite).where(
            OrganizationInvite.token_hash == token_hash,
            OrganizationInvite.expires_at > datetime.now(timezone.utc),
            OrganizationInvite.accepted_at == None,
        )
    )
    return result.scalar_one_or_none()


async def consume_invite(db: AsyncSession, invite: OrganizationInvite) -> None:
    invite.accepted_at = datetime.now(timezone.utc)
    await db.commit()


async def get_invite_detail(
    db: AsyncSession, raw_token: str
) -> Optional[dict]:
    invite = await get_invite_by_token(db, raw_token)
    if not invite:
        return None

    inviter_result = await db.execute(
        select(User).where(User.id == invite.invited_by_id)
    )
    inviter = inviter_result.scalar_one_or_none()

    from multitenancy.organizations.organization import Organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == invite.organization_id)
    )
    org = org_result.scalar_one_or_none()

    return {
        "email": invite.email,
        "organization_name": org.name if org else "Unknown Organization",
        "role": invite.role.value if hasattr(invite.role, "value") else str(invite.role),
        "inviter_name": inviter.full_name if inviter else "A team member",
        "expires_at": invite.expires_at.isoformat(),
    }

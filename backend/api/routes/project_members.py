# backend/api/routes/project_members.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import DateTime, Enum as SAEnum, UniqueConstraint, delete, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from api.dependencies import CurrentUser, get_db
from database.base import Base, TimestampMixin, UUIDMixin
from database.models.project import Project
from database.models.user import User
from settings import Role

router = APIRouter()


class ProjectMember(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    project_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    role: Mapped[Role] = mapped_column(SAEnum(Role, name="user_role", native_enum=False), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AddMemberRequest(BaseModel):
    user_id: str
    role: str


class UpdateMemberRequest(BaseModel):
    role: str


def _validate_role(role_str: str) -> Role:
    try:
        return Role(role_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Valid: {[r.value for r in Role]}",
        )


async def _get_project_or_404(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return p


def _member_response(member: ProjectMember, user: User) -> dict:
    return {
        "user_id": str(member.user_id),
        "name": user.full_name,
        "email": user.email,
        "role": member.role.value if hasattr(member.role, "value") else str(member.role),
        "joined_at": member.joined_at.isoformat(),
    }


@router.get("/{project_id}/members", status_code=status.HTTP_200_OK)
async def list_project_members(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    await _get_project_or_404(db, project_id, user.organization_id)

    members_result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    members = members_result.scalars().all()
    if not members:
        return []

    user_ids = [m.user_id for m in members]
    users_map = {
        u.id: u
        for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    }
    return [_member_response(m, users_map[m.user_id]) for m in members if m.user_id in users_map]


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: uuid.UUID,
    payload: AddMemberRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    if user.role not in {Role.ADMIN, Role.OWNER, Role.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    await _get_project_or_404(db, project_id, user.organization_id)
    role = _validate_role(payload.role)

    try:
        target_uid = uuid.UUID(payload.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user_id")

    target = (await db.execute(
        select(User).where(
            User.id == target_uid,
            User.organization_id == user.organization_id,
            User.is_active == True,
        )
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in your organization")

    if (await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_uid,
        )
    )).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member")

    member = ProjectMember(
        project_id=project_id,
        user_id=target_uid,
        role=role,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return _member_response(member, target)


@router.patch("/{project_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def update_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateMemberRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    if user.role not in {Role.ADMIN, Role.OWNER, Role.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    await _get_project_or_404(db, project_id, user.organization_id)
    role = _validate_role(payload.role)

    member = (await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member.role = role
    await db.commit()
    await db.refresh(member)

    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    return _member_response(member, target)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    if user.role not in {Role.ADMIN, Role.OWNER, Role.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove yourself")

    await _get_project_or_404(db, project_id, user.organization_id)

    result = await db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

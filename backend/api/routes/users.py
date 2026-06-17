# api/routes/users.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from api.dependencies import CurrentUser, Pagination, get_db
from settings import Role

router = APIRouter()


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str


class UpdateUserRoleRequest(BaseModel):
    role: str


@router.get("/users")
async def list_users(user: CurrentUser, pagination: Pagination, db=Depends(get_db)) -> list[dict[str, Any]]:
    from database.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    if user.organization_id is None:
        return []
    users = await repo.list_by_organization(
        user.organization_id, offset=pagination.offset, limit=pagination.limit
    )
    return [
        {
            "id": str(u.id),
            "name": u.full_name,
            "email": u.email,
            "role": u.role.value,
            "status": "active" if u.is_active else "inactive",
            "joined_at": u.created_at.isoformat(),
            "avatar_url": None,
        }
        for u in users
    ]


@router.post("/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteUserRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from multitenancy.tenant_manager import TenantManager
    from database.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    invitee = await user_repo.get_by_email(body.email)

    if user.organization_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No organization context")

    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {body.role}")

    if invitee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User with that email not found")

    manager = TenantManager(db)
    await manager.invite_member(
        organization_id=user.organization_id,
        user_id=invitee.id,
        role=role,
        invited_by=user.id,
    )
    await db.commit()
    return {"message": f"Invitation sent to {body.email}", "email": body.email, "role": body.role}


@router.patch("/users/{user_id}")
async def update_user_role(
    user_id: str,
    body: UpdateUserRoleRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    import uuid as _uuid
    from multitenancy.tenant_manager import TenantManager

    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {body.role}")

    if user.organization_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No organization context")

    manager = TenantManager(db)
    await manager.update_member_role(
        organization_id=user.organization_id,
        user_id=_uuid.UUID(user_id),
        new_role=role,
        actor_role=user.role,
    )
    await db.commit()
    return {"user_id": user_id, "role": body.role}


@router.post("/users/{user_id}/remove", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_user(
    user_id: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> Response:
    import uuid as _uuid
    from multitenancy.tenant_manager import TenantManager

    if user.organization_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No organization context")

    manager = TenantManager(db)
    await manager.remove_member(
        organization_id=user.organization_id,
        user_id=_uuid.UUID(user_id),
        actor_role=user.role,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

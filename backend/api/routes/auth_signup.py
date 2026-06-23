# backend/api/routes/auth_signup.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import create_access_token, set_auth_cookie
from auth.password import get_password_hash, verify_password, validate_password_strength
from database.models.user import User
from database.session import get_db
from dependencies import get_current_user
from multitenancy.organizations.organization import Organization
from services.email_service import (
    send_invite_email,
    send_password_reset_email,
    send_verification_email,
)
from services.invite_service import (
    OrganizationInvite,
    consume_invite,
    create_invite,
    get_invite_by_token,
    get_invite_detail,
)
from services.token_service import (
    consume_email_verification_token,
    consume_password_reset_token,
    create_email_verification_token,
    create_password_reset_token,
    verify_email_token,
    verify_password_reset_token,
)
from settings import Role, settings

router = APIRouter()


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    organization_name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError(errors[0])
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError(errors[0])
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError(errors[0])
        return v


def _user_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "tenant_id": str(user.organization_id) if user.organization_id else None,
        "avatar_url": user.metadata_.get("avatar_url") if user.metadata_ else None,
        "is_verified": user.is_verified,
        "mfa_enabled": user.mfa_enabled,
        "created_at": user.created_at.isoformat() if hasattr(user, "created_at") else None,
    }


async def _login_user(response: Response, user: User) -> dict:
    token_data = {
        "sub": str(user.id),
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "tenant_id": str(user.organization_id) if user.organization_id else None,
    }
    access_token = create_access_token(token_data)
    set_auth_cookie(response, access_token)
    return _user_response(user)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    hashed_pw = get_password_hash(payload.password)

    org_id: Optional[uuid.UUID] = None
    if payload.organization_name:
        org = Organization(
            name=payload.organization_name.strip(),
            slug=payload.organization_name.strip().lower().replace(" ", "-"),
        )
        db.add(org)
        await db.flush()
        org_id = org.id

    user = User(
        email=payload.email,
        full_name=payload.name.strip(),
        hashed_password=hashed_pw,
        role=Role.OWNER if payload.organization_name else Role.VIEWER,
        organization_id=org_id,
        is_verified=False,
        mfa_enabled=False,
        metadata_={},
    )
    db.add(user)
    await db.flush()

    if org_id:
        from multitenancy.organizations.members import OrganizationMember
        member = OrganizationMember(
            organization_id=org_id,
            user_id=user.id,
            role=Role.OWNER,
        )
        db.add(member)

    await db.commit()
    await db.refresh(user)

    raw_token = await create_email_verification_token(db, user)
    background_tasks.add_task(
        send_verification_email, user.email, user.full_name, raw_token
    )

    return await _login_user(response, user)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(User).where(User.email == payload.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user:
        raw_token = await create_password_reset_token(db, user)
        background_tasks.add_task(
            send_password_reset_email, user.email, user.full_name, raw_token
        )

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await verify_password_reset_token(db, payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    user.hashed_password = get_password_hash(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    await consume_password_reset_token(db, user)
    await db.commit()

    return {"message": "Password updated successfully"}


@router.post("/verify-email/request", status_code=status.HTTP_200_OK)
async def request_email_verification(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if current_user.is_verified:
        return {"message": "Email already verified"}

    raw_token = await create_email_verification_token(db, current_user)
    background_tasks.add_task(
        send_verification_email,
        current_user.email,
        current_user.full_name,
        raw_token,
    )
    return {"message": "Verification email sent"}


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await verify_email_token(db, payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    await consume_email_verification_token(db, user)
    return {"message": "Email verified"}


@router.get("/invite/{token}", status_code=status.HTTP_200_OK)
async def get_invite_info(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    detail = await get_invite_detail(db, token)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite",
        )
    return detail


@router.post("/accept-invite", status_code=status.HTTP_200_OK)
async def accept_invite(
    payload: AcceptInviteRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    invite = await get_invite_by_token(db, payload.token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invalid or expired invite",
        )

    existing = await db.execute(select(User).where(User.email == invite.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please log in.",
        )

    hashed_pw = get_password_hash(payload.password)
    user = User(
        email=invite.email,
        full_name=payload.name.strip(),
        hashed_password=hashed_pw,
        role=invite.role,
        organization_id=invite.organization_id,
        is_verified=True,
        mfa_enabled=False,
        metadata_={},
    )
    db.add(user)
    await db.flush()

    from multitenancy.organizations.members import OrganizationMember
    member = OrganizationMember(
        organization_id=invite.organization_id,
        user_id=user.id,
        role=invite.role,
    )
    db.add(member)

    await consume_invite(db, invite)
    await db.commit()
    await db.refresh(user)

    return await _login_user(response, user)

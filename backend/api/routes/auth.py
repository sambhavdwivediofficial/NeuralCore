# backend/api/routes/auth.py
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, EmailStr, Field

from api.dependencies import CurrentUser, get_app_settings, get_db, get_redis
from api.exceptions import NotFoundError
from settings import Settings

router = APIRouter()

_MFA_CHALLENGE_STORE: dict[str, dict] = {}
_MFA_CHALLENGE_TTL_SECONDS = 300


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MFAChallengeRequest(BaseModel):
    challenge_token: str
    code: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MFAToggleRequest(BaseModel):
    enabled: bool


class MFAVerifyRequest(BaseModel):
    code: str


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scope: str = Field(default="read", pattern="^(read|write|admin)$")


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


def _set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key="nc_access_token",
        value=token,
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=settings.auth.jwt.access_token_expire_minutes * 60,
    )


def _build_user_response(user: Any) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.full_name,
        "role": user.role.value,
        "tenant_id": str(user.organization_id) if user.organization_id else None,
        "avatar_url": user.metadata_.get("avatar_url") if user.metadata_ else None,
        "is_verified": user.is_verified,
        "mfa_enabled": user.mfa_enabled,
        "created_at": user.created_at.isoformat(),
    }


def _create_mfa_challenge(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _MFA_CHALLENGE_STORE[token] = {
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=_MFA_CHALLENGE_TTL_SECONDS),
    }
    return token


def _consume_mfa_challenge(token: str) -> Optional[str]:
    entry = _MFA_CHALLENGE_STORE.pop(token, None)
    if not entry:
        return None
    if entry["expires_at"] < datetime.now(timezone.utc):
        return None
    return entry["user_id"]


def _purge_expired_challenges() -> None:
    now = datetime.now(timezone.utc)
    expired = [k for k, v in _MFA_CHALLENGE_STORE.items() if v["expires_at"] < now]
    for k in expired:
        _MFA_CHALLENGE_STORE.pop(k, None)


@router.post("/login")
async def login(
    request_body: LoginRequest,
    request: Request,
    response: Response,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> ORJSONResponse:
    from auth.jwt import create_access_token
    from auth.password import verify_password
    from database.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(request_body.email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is temporarily locked",
        )

    if user.hashed_password is None or not verify_password(request_body.password, user.hashed_password):
        await user_repo.increment_failed_attempts(user)
        if user.failed_login_attempts + 1 >= settings.auth.account_lockout.max_failed_attempts:
            lockout_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.auth.account_lockout.lockout_duration_minutes
            )
            await user_repo.lock_account(user, lockout_until)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await user_repo.reset_failed_attempts(user)
    await user_repo.update_last_login(user)
    await db.commit()

    if user.mfa_enabled and user.mfa_secret:
        _purge_expired_challenges()
        challenge_token = _create_mfa_challenge(str(user.id))
        return ORJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "mfa_required": True,
                "challenge_token": challenge_token,
            },
        )

    token = create_access_token(user, settings)
    resp = ORJSONResponse(content=_build_user_response(user))
    _set_auth_cookie(resp, token, settings)
    return resp


@router.post("/mfa/challenge")
async def mfa_challenge(
    body: MFAChallengeRequest,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> ORJSONResponse:
    from auth.jwt import create_access_token
    from auth.mfa import verify_totp_code, verify_recovery_code
    from database.repositories.user_repository import UserRepository

    user_id = _consume_mfa_challenge(body.challenge_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired MFA challenge token",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    totp_valid = (
        user.mfa_secret is not None
        and verify_totp_code(user.mfa_secret, body.code, settings)
    )

    recovery_valid = False
    if not totp_valid and user.mfa_recovery_codes:
        recovery_valid, remaining_codes = verify_recovery_code(body.code, user.mfa_recovery_codes)
        if recovery_valid:
            await user_repo.update(user.id, mfa_recovery_codes=remaining_codes)
            await db.commit()

    if not totp_valid and not recovery_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    await user_repo.update_last_login(user)
    await db.commit()

    token = create_access_token(user, settings)
    resp = ORJSONResponse(content=_build_user_response(user))
    _set_auth_cookie(resp, token, settings)
    return resp


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key="nc_access_token", path="/")
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> ORJSONResponse:
    from auth.jwt import create_access_token, decode_access_token
    from database.repositories.user_repository import UserRepository

    token = request.cookies.get("nc_access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    try:
        payload = decode_access_token(token, settings)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(payload.sub))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_token = create_access_token(user, settings)
    resp = ORJSONResponse(content={"message": "Token refreshed"})
    _set_auth_cookie(resp, new_token, settings)
    return resp


@router.get("/me")
async def get_me(user: CurrentUser) -> dict[str, Any]:
    return _build_user_response(user)


@router.patch("/me")
async def update_me(
    body: UserUpdateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    updates: dict[str, Any] = {}
    if body.name is not None:
        updates["full_name"] = body.name
    if body.bio is not None:
        updates["bio"] = body.bio

    if updates:
        updated = await repo.update(user.id, **updates)
        await db.commit()
        return _build_user_response(updated or user)
    return _build_user_response(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    from auth.password import hash_password, validate_password_strength, verify_password
    from database.repositories.user_repository import UserRepository

    if user.hashed_password is None or not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    validate_password_strength(body.new_password, settings)
    repo = UserRepository(db)
    await repo.update(user.id, hashed_password=hash_password(body.new_password, settings))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mfa/enable")
async def mfa_enable(
    user: CurrentUser,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from auth.mfa import build_provisioning_uri, generate_totp_secret
    from database.repositories.user_repository import UserRepository

    secret = generate_totp_secret()
    repo = UserRepository(db)
    await repo.update(user.id, mfa_secret=secret)
    await db.commit()
    uri = build_provisioning_uri(secret, user.email, settings)
    return {"provisioning_uri": uri, "secret": secret}


@router.post("/mfa/verify", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def mfa_verify(
    body: MFAVerifyRequest,
    user: CurrentUser,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    from auth.mfa import generate_recovery_codes, hash_recovery_codes, verify_totp_code
    from database.repositories.user_repository import UserRepository

    if not user.mfa_secret or not verify_totp_code(user.mfa_secret, body.code, settings):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    codes = generate_recovery_codes(settings)
    hashed = hash_recovery_codes(codes)
    repo = UserRepository(db)
    await repo.update(user.id, mfa_enabled=True, mfa_recovery_codes=hashed)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def mfa_disable(user: CurrentUser, db=Depends(get_db)) -> Response:
    from database.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    await repo.update(user.id, mfa_enabled=False, mfa_secret=None, mfa_recovery_codes=None)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mfa/toggle")
async def mfa_toggle(
    body: MFAToggleRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    await repo.update(user.id, mfa_enabled=body.enabled)
    await db.commit()
    return {"mfa_enabled": body.enabled}


@router.get("/sessions")
async def list_sessions(
    user: CurrentUser,
    redis=Depends(get_redis),
) -> list[dict[str, Any]]:
    return [
        {
            "id": "current",
            "device": "Current session",
            "location": "Unknown",
            "last_active_at": datetime.now(timezone.utc).isoformat(),
            "is_current": True,
        }
    ]


@router.post("/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def revoke_session(session_id: str, user: CurrentUser) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api-keys")
async def list_api_keys(
    user: CurrentUser,
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    return []


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: APIKeyCreateRequest,
    user: CurrentUser,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from auth.api_keys import generate_api_key

    generated = generate_api_key(settings)
    return {
        "id": uuid.uuid4().hex,
        "name": body.name,
        "scope": body.scope,
        "prefix": generated.raw_key[:8],
        "secret": generated.raw_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used_at": None,
        "expires_at": generated.expires_at.isoformat() if generated.expires_at else None,
    }


@router.post("/api-keys/{key_id}/revoke", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def revoke_api_key(key_id: str, user: CurrentUser) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)

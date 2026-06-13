# auth/jwt.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt
from pydantic import BaseModel, ConfigDict

from database.models.user import User
from settings import Settings


class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(ValueError):
    pass


class TokenExpiredError(InvalidTokenError):
    pass


class JWTPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    sub: str
    email: str
    role: str
    organization_id: str | None = None
    token_type: TokenType
    jti: str
    iss: str
    aud: str
    iat: int
    exp: int

    @property
    def user_id(self) -> uuid.UUID:
        return uuid.UUID(self.sub)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_claims(user: User, settings: Settings, token_type: TokenType, expires_delta: timedelta) -> dict[str, Any]:
    now = _now()
    return {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "token_type": token_type.value,
        "jti": uuid.uuid4().hex,
        "iss": settings.auth.jwt.issuer,
        "aud": settings.auth.jwt.audience,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }


def _signing_key(settings: Settings) -> str:
    if settings.auth.jwt.private_key is None:
        raise InvalidTokenError("JWT private key is not configured")
    return settings.auth.jwt.private_key.get_secret_value()


def _verification_key(settings: Settings) -> str:
    if settings.auth.jwt.public_key is None:
        raise InvalidTokenError("JWT public key is not configured")
    return settings.auth.jwt.public_key.get_secret_value()


def create_access_token(user: User, settings: Settings) -> str:
    claims = _build_claims(
        user, settings, TokenType.ACCESS, timedelta(minutes=settings.auth.jwt.access_token_expire_minutes)
    )
    return pyjwt.encode(claims, _signing_key(settings), algorithm=settings.auth.jwt.algorithm)


def create_refresh_token(user: User, settings: Settings) -> str:
    claims = _build_claims(
        user, settings, TokenType.REFRESH, timedelta(days=settings.auth.jwt.refresh_token_expire_days)
    )
    return pyjwt.encode(claims, _signing_key(settings), algorithm=settings.auth.jwt.algorithm)


def create_token_pair(user: User, settings: Settings) -> tuple[str, str]:
    return create_access_token(user, settings), create_refresh_token(user, settings)


def _decode(token: str, settings: Settings, expected_type: TokenType) -> JWTPayload:
    try:
        raw = pyjwt.decode(
            token,
            _verification_key(settings),
            algorithms=[settings.auth.jwt.algorithm],
            audience=settings.auth.jwt.audience,
            issuer=settings.auth.jwt.issuer,
            leeway=settings.auth.jwt.leeway_seconds,
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except pyjwt.InvalidTokenError as exc:
        raise InvalidTokenError(f"Invalid token: {exc}") from exc

    payload = JWTPayload.model_validate(raw)
    if payload.token_type != expected_type:
        raise InvalidTokenError(f"Expected {expected_type.value} token, got {payload.token_type.value}")
    return payload


def decode_access_token(token: str, settings: Settings) -> JWTPayload:
    return _decode(token, settings, TokenType.ACCESS)


def decode_refresh_token(token: str, settings: Settings) -> JWTPayload:
    return _decode(token, settings, TokenType.REFRESH)
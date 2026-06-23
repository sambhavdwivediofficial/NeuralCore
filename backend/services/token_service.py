# backend/services/token_service.py
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User


TOKEN_BYTES = 32
PASSWORD_RESET_EXPIRE_HOURS = 1
EMAIL_VERIFY_EXPIRE_HOURS = 24
INVITE_EXPIRE_HOURS = 72


def _generate_raw_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_password_reset_token(db: AsyncSession, user: User) -> str:
    raw = _generate_raw_token()
    hashed = _hash_token(raw)
    expires = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            password_reset_token=hashed,
            password_reset_expires_at=expires,
        )
    )
    await db.commit()
    return raw


async def verify_password_reset_token(
    db: AsyncSession, raw_token: str
) -> Optional[User]:
    hashed = _hash_token(raw_token)
    result = await db.execute(
        select(User).where(
            User.password_reset_token == hashed,
            User.password_reset_expires_at > datetime.now(timezone.utc),
            User.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def consume_password_reset_token(db: AsyncSession, user: User) -> None:
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            password_reset_token=None,
            password_reset_expires_at=None,
        )
    )
    await db.commit()


async def create_email_verification_token(db: AsyncSession, user: User) -> str:
    raw = _generate_raw_token()
    hashed = _hash_token(raw)
    expires = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFY_EXPIRE_HOURS)
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            verification_token=hashed,
            verification_token_expires_at=expires,
        )
    )
    await db.commit()
    return raw


async def verify_email_token(
    db: AsyncSession, raw_token: str
) -> Optional[User]:
    hashed = _hash_token(raw_token)
    result = await db.execute(
        select(User).where(
            User.verification_token == hashed,
            User.verification_token_expires_at > datetime.now(timezone.utc),
            User.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def consume_email_verification_token(db: AsyncSession, user: User) -> None:
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            is_verified=True,
            verification_token=None,
            verification_token_expires_at=None,
        )
    )
    await db.commit()


def generate_invite_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_invite_token(raw_token: str) -> str:
    return _hash_token(raw_token)


def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())

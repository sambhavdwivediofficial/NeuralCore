# auth/password.py
from __future__ import annotations

import re

from passlib.context import CryptContext

from auth.validators import ValidationError
from settings import Settings

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,
    deprecated="auto",
)


def hash_password(password: str, settings: Settings) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(password, hashed_password)


def needs_rehash(hashed_password: str, settings: Settings) -> bool:
    return _pwd_context.needs_update(hashed_password)


def validate_password_strength(password: str, settings: Settings) -> None:
    policy = settings.auth.password_policy
    errors: list[str] = []
    if len(password) < policy.min_length:
        errors.append(f"Password must be at least {policy.min_length} characters long")
    if policy.require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if policy.require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if policy.require_number and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")
    if policy.require_special and not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must contain at least one special character")
    if errors:
        raise ValidationError("; ".join(errors))
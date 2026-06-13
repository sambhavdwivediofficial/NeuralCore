# auth/api_keys.py
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from settings import Settings


@dataclass(slots=True, frozen=True)
class GeneratedAPIKey:
    raw_key: str
    key_hash: str
    prefix: str
    expires_at: datetime | None


def generate_api_key(settings: Settings) -> GeneratedAPIKey:
    config = settings.auth.api_keys
    token = secrets.token_urlsafe(config.length)
    raw_key = f"{config.prefix}{token}"
    key_hash = hash_api_key(raw_key, settings)
    expires_at = None
    if config.default_expire_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=config.default_expire_days)
    return GeneratedAPIKey(raw_key=raw_key, key_hash=key_hash, prefix=config.prefix, expires_at=expires_at)


def hash_api_key(raw_key: str, settings: Settings) -> str:
    hasher = hashlib.new(settings.auth.api_keys.hash_algorithm)
    hasher.update(raw_key.encode("utf-8"))
    return hasher.hexdigest()


def verify_api_key(raw_key: str, key_hash: str, settings: Settings) -> bool:
    return secrets.compare_digest(hash_api_key(raw_key, settings), key_hash)


def is_api_key_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    return datetime.now(timezone.utc) >= expires_at


def has_valid_prefix(raw_key: str, settings: Settings) -> bool:
    return raw_key.startswith(settings.auth.api_keys.prefix)
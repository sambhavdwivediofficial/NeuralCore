# auth/mfa.py
from __future__ import annotations

import hashlib
import secrets

import pyotp

from settings import Settings


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_provisioning_uri(secret: str, email: str, settings: Settings) -> str:
    totp = pyotp.TOTP(secret, digits=settings.auth.mfa.digits, interval=settings.auth.mfa.period_seconds)
    return totp.provisioning_uri(name=email, issuer_name=settings.auth.mfa.issuer_name)


def verify_totp_code(secret: str, code: str, settings: Settings) -> bool:
    totp = pyotp.TOTP(secret, digits=settings.auth.mfa.digits, interval=settings.auth.mfa.period_seconds)
    return totp.verify(code, valid_window=1)


def generate_recovery_codes(settings: Settings) -> list[str]:
    return [secrets.token_hex(5) for _ in range(settings.auth.mfa.recovery_codes_count)]


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def hash_recovery_codes(codes: list[str]) -> list[str]:
    return [hash_recovery_code(code) for code in codes]


def verify_recovery_code(code: str, hashed_codes: list[str]) -> tuple[bool, list[str]]:
    code_hash = hash_recovery_code(code)
    if code_hash in hashed_codes:
        remaining = [item for item in hashed_codes if item != code_hash]
        return True, remaining
    return False, hashed_codes
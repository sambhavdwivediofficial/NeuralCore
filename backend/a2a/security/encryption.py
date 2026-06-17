# a2a/security/encryption.py
from __future__ import annotations

import base64
import hashlib
import os
from typing import Any


class EncryptionError(ValueError):
    pass


def _derive_key(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations=100_000, dklen=32)


def encrypt_payload(payload: str, secret: str) -> str:
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(_derive_key(secret, b"neuralcore_a2a"))
        fernet = Fernet(key)
        encrypted = fernet.encrypt(payload.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")
    except ImportError:
        return _xor_obfuscate(payload, secret)


def decrypt_payload(encrypted: str, secret: str) -> str:
    try:
        from cryptography.fernet import Fernet, InvalidToken
        key = base64.urlsafe_b64encode(_derive_key(secret, b"neuralcore_a2a"))
        fernet = Fernet(key)
        raw = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
        return fernet.decrypt(raw).decode("utf-8")
    except ImportError:
        return _xor_obfuscate(encrypted, secret)
    except Exception as exc:
        raise EncryptionError(f"Decryption failed: {exc}") from exc


def _xor_obfuscate(data: str, key: str) -> str:
    key_bytes = hashlib.sha256(key.encode()).digest()
    data_bytes = data.encode("utf-8")
    result = bytes(b ^ key_bytes[i % 32] for i, b in enumerate(data_bytes))
    return base64.urlsafe_b64encode(result).decode("utf-8")


def hash_sensitive_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

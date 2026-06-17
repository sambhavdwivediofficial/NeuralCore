# a2a/security/authentication.py
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.security.auth")

_TOKEN_TTL = 3600
_SIGNATURE_HEADER = "x-a2a-signature"
_TIMESTAMP_HEADER = "x-a2a-timestamp"
_AGENT_ID_HEADER = "x-a2a-agent-id"
_MAX_CLOCK_SKEW = 30


@dataclass(slots=True, frozen=True)
class A2ACredential:
    agent_id: str
    shared_secret: str
    issued_at: float = 0.0
    expires_at: float = 0.0


def generate_agent_secret() -> str:
    return secrets.token_urlsafe(48)


def sign_message(payload: str, secret: str, timestamp: float | None = None) -> str:
    ts = str(int(timestamp or time.time()))
    signing_string = f"{ts}.{payload}"
    return hmac.new(secret.encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(
    payload: str,
    signature: str,
    secret: str,
    timestamp: float,
) -> bool:
    now = time.time()
    if abs(now - timestamp) > _MAX_CLOCK_SKEW:
        logger.warning("a2a_auth_clock_skew", skew=abs(now - timestamp))
        return False
    expected = sign_message(payload, secret, timestamp)
    return hmac.compare_digest(expected, signature)


def build_auth_headers(
    agent_id: str, payload: str, secret: str
) -> dict[str, str]:
    ts = time.time()
    signature = sign_message(payload, secret, ts)
    return {
        _AGENT_ID_HEADER: agent_id,
        _TIMESTAMP_HEADER: str(int(ts)),
        _SIGNATURE_HEADER: signature,
    }


def verify_auth_headers(
    headers: dict[str, str],
    payload: str,
    secret_resolver: Any,
) -> bool:
    agent_id = headers.get(_AGENT_ID_HEADER)
    timestamp_str = headers.get(_TIMESTAMP_HEADER)
    signature = headers.get(_SIGNATURE_HEADER)

    if not agent_id or not timestamp_str or not signature:
        return False

    try:
        timestamp = float(timestamp_str)
    except ValueError:
        return False

    secret = secret_resolver(agent_id)
    if not secret:
        return False

    return verify_signature(payload, signature, secret, timestamp)

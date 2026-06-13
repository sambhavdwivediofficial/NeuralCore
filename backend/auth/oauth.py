# auth/oauth.py
from __future__ import annotations

import secrets
import urllib.parse
from dataclasses import dataclass

import httpx

from settings import Settings


class OAuthError(Exception):
    pass


class UnsupportedProviderError(OAuthError):
    pass


@dataclass(slots=True, frozen=True)
class OAuthUserInfo:
    provider: str
    subject: str
    email: str
    full_name: str
    avatar_url: str | None = None
    email_verified: bool = False


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def _get_provider_config(provider: str, settings: Settings):
    provider_config = settings.auth.oauth.providers.get(provider)
    if provider_config is None or not provider_config.enabled:
        raise UnsupportedProviderError(f"OAuth provider '{provider}' is not enabled")
    if not provider_config.client_id or not provider_config.redirect_uri:
        raise OAuthError(f"OAuth provider '{provider}' is missing client configuration")
    return provider_config


def build_authorization_url(provider: str, settings: Settings, state: str) -> str:
    config = _get_provider_config(provider, settings)
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{config.authorize_url}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(provider: str, code: str, settings: Settings) -> dict[str, str]:
    config = _get_provider_config(provider, settings)
    if config.client_secret is None:
        raise OAuthError(f"OAuth provider '{provider}' is missing a client secret")
    payload = {
        "client_id": config.client_id,
        "client_secret": config.client_secret.get_secret_value(),
        "code": code,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(config.token_url, data=payload, headers={"Accept": "application/json"})
    if response.status_code >= 400:
        raise OAuthError(f"Failed to exchange code with {provider}: {response.text}")
    return response.json()


async def fetch_user_info(provider: str, access_token: str, settings: Settings) -> OAuthUserInfo:
    config = _get_provider_config(provider, settings)
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(config.userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code >= 400:
        raise OAuthError(f"Failed to fetch user info from {provider}: {response.text}")
    return _normalize_user_info(provider, response.json())


def _normalize_user_info(provider: str, data: dict) -> OAuthUserInfo:
    if provider == "google":
        return OAuthUserInfo(
            provider=provider,
            subject=data["sub"],
            email=data["email"],
            full_name=data.get("name", data.get("email", "")),
            avatar_url=data.get("picture"),
            email_verified=bool(data.get("email_verified", False)),
        )
    if provider == "github":
        return OAuthUserInfo(
            provider=provider,
            subject=str(data["id"]),
            email=data.get("email") or f"{data['login']}@users.noreply.github.com",
            full_name=data.get("name") or data.get("login", ""),
            avatar_url=data.get("avatar_url"),
            email_verified=bool(data.get("email")),
        )
    if provider == "microsoft":
        return OAuthUserInfo(
            provider=provider,
            subject=data["sub"],
            email=data.get("email") or data.get("preferred_username", ""),
            full_name=data.get("name", ""),
            avatar_url=None,
            email_verified=True,
        )
    raise UnsupportedProviderError(f"Unknown OAuth provider '{provider}'")
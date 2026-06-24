# backend/api/routes/auth_oauth.py
from __future__ import annotations

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from auth.jwt import create_access_token
from database.models.user import User
from settings import Role, get_settings

router = APIRouter()

_OAUTH_STATE_STORE: dict[str, str] = {}

PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": "openid email profile",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scopes": "read:user user:email",
    },
    "microsoft": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": "openid email profile User.Read",
    },
}


def _get_client_id(provider: str) -> str:
    settings = get_settings()
    mapping = {
        "google": settings.auth.oauth.google.client_id,
        "github": settings.auth.oauth.github.client_id,
        "microsoft": settings.auth.oauth.microsoft.client_id,
    }
    return mapping[provider]


def _get_client_secret(provider: str) -> str:
    settings = get_settings()
    mapping = {
        "google": settings.auth.oauth.google.client_secret.get_secret_value(),
        "github": settings.auth.oauth.github.client_secret.get_secret_value(),
        "microsoft": settings.auth.oauth.microsoft.client_secret.get_secret_value(),
    }
    return mapping[provider]


def _get_redirect_uri(provider: str) -> str:
    settings = get_settings()
    return f"{settings.app.api_url}/api/v1/auth/oauth/{provider}/callback"


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="nc_access_token",
        value=token,
        httponly=False,
        secure=False,
        samesite="lax",
        path="/",
        max_age=60 * 15,
    )


async def _upsert_oauth_user(
    db: AsyncSession,
    provider: str,
    oauth_subject: str,
    email: str,
    full_name: str,
    avatar_url: Optional[str],
) -> User:
    from datetime import datetime, timezone

    result = await db.execute(
        select(User).where(
            User.oauth_provider == provider,
            User.oauth_subject == oauth_subject,
        )
    )
    user = result.scalar_one_or_none()

    if user:
        user.last_login_at = datetime.now(timezone.utc)
        if avatar_url and user.metadata_:
            user.metadata_["avatar_url"] = avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    by_email = await db.execute(select(User).where(User.email == email))
    existing = by_email.scalar_one_or_none()
    if existing:
        existing.oauth_provider = provider
        existing.oauth_subject = oauth_subject
        existing.is_verified = True
        if avatar_url and existing.metadata_ is not None:
            existing.metadata_["avatar_url"] = avatar_url
        await db.commit()
        await db.refresh(existing)
        return existing

    new_user = User(
        email=email,
        full_name=full_name,
        hashed_password=None,
        role=Role.VIEWER,
        oauth_provider=provider,
        oauth_subject=oauth_subject,
        is_verified=True,
        mfa_enabled=False,
        metadata_={"avatar_url": avatar_url} if avatar_url else {},
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def _exchange_code_google(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            PROVIDERS["google"]["token_url"],
            data={
                "code": code,
                "client_id": _get_client_id("google"),
                "client_secret": _get_client_secret("google"),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

        userinfo_resp = await client.get(
            PROVIDERS["google"]["userinfo_url"],
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        info = userinfo_resp.json()

    return {
        "sub": info["sub"],
        "email": info["email"],
        "name": info.get("name", info["email"].split("@")[0]),
        "avatar_url": info.get("picture"),
    }


async def _exchange_code_github(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            PROVIDERS["github"]["token_url"],
            data={
                "code": code,
                "client_id": _get_client_id("github"),
                "client_secret": _get_client_secret("github"),
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        user_resp = await client.get(PROVIDERS["github"]["userinfo_url"], headers=headers)
        user_resp.raise_for_status()
        user_data = user_resp.json()

        email = user_data.get("email")
        if not email:
            emails_resp = await client.get(PROVIDERS["github"]["emails_url"], headers=headers)
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")), None
            )
            if not primary:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No verified primary email found on GitHub account",
                )
            email = primary["email"]

    return {
        "sub": str(user_data["id"]),
        "email": email,
        "name": user_data.get("name") or user_data.get("login", email.split("@")[0]),
        "avatar_url": user_data.get("avatar_url"),
    }


async def _exchange_code_microsoft(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            PROVIDERS["microsoft"]["token_url"],
            data={
                "code": code,
                "client_id": _get_client_id("microsoft"),
                "client_secret": _get_client_secret("microsoft"),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": PROVIDERS["microsoft"]["scopes"],
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

        graph_resp = await client.get(
            PROVIDERS["microsoft"]["userinfo_url"],
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        graph_resp.raise_for_status()
        info = graph_resp.json()

    email = info.get("mail") or info.get("userPrincipalName", "")
    return {
        "sub": info["id"],
        "email": email,
        "name": info.get("displayName", email.split("@")[0]),
        "avatar_url": None,
    }


_EXCHANGE_HANDLERS = {
    "google": _exchange_code_google,
    "github": _exchange_code_github,
    "microsoft": _exchange_code_microsoft,
}


@router.get("/oauth/{provider}")
async def oauth_login(provider: str) -> RedirectResponse:
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown OAuth provider: {provider}",
        )

    state = secrets.token_urlsafe(32)
    _OAUTH_STATE_STORE[state] = provider

    cfg = PROVIDERS[provider]
    params = {
        "client_id": _get_client_id(provider),
        "redirect_uri": _get_redirect_uri(provider),
        "scope": cfg["scopes"],
        "state": state,
        "response_type": "code",
    }

    if provider == "google":
        params["access_type"] = "offline"
        params["prompt"] = "select_account"
    elif provider == "microsoft":
        params["response_mode"] = "query"

    auth_url = cfg["auth_url"] + "?" + urlencode(params)
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    app_url = settings.app.app_url
    error_base = f"{app_url}/auth/callback?status=error"

    if provider not in PROVIDERS:
        return RedirectResponse(
            url=f"{error_base}&message=Unknown+provider",
            status_code=status.HTTP_302_FOUND,
        )

    if error:
        return RedirectResponse(
            url=f"{error_base}&message={error}",
            status_code=status.HTTP_302_FOUND,
        )

    if not state or state not in _OAUTH_STATE_STORE:
        return RedirectResponse(
            url=f"{error_base}&message=Invalid+state+parameter",
            status_code=status.HTTP_302_FOUND,
        )

    _OAUTH_STATE_STORE.pop(state, None)

    if not code:
        return RedirectResponse(
            url=f"{error_base}&message=No+authorization+code+received",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        handler = _EXCHANGE_HANDLERS[provider]
        user_info = await handler(code, _get_redirect_uri(provider))
    except Exception:
        return RedirectResponse(
            url=f"{error_base}&message=OAuth+authentication+failed",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        user = await _upsert_oauth_user(
            db=db,
            provider=provider,
            oauth_subject=user_info["sub"],
            email=user_info["email"],
            full_name=user_info["name"],
            avatar_url=user_info.get("avatar_url"),
        )
    except Exception:
        return RedirectResponse(
            url=f"{error_base}&message=Failed+to+create+user+account",
            status_code=status.HTTP_302_FOUND,
        )

    token = create_access_token(user, settings)
    success_redirect = RedirectResponse(
        url=f"{app_url}/auth/callback?status=success",
        status_code=status.HTTP_302_FOUND,
    )
    _set_auth_cookie(success_redirect, token)
    return success_redirect

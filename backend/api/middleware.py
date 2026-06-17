# api/middleware.py
from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from monitoring.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from settings import Settings


class RequestContextMiddleware:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        request.state.start_time = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


class SecurityHeadersMiddleware:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._headers = settings.app.security_headers

    async def __call__(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = self._headers.x_frame_options
        response.headers["X-Content-Type-Options"] = self._headers.x_content_type_options
        response.headers["Referrer-Policy"] = self._headers.referrer_policy
        response.headers["Permissions-Policy"] = self._headers.permissions_policy
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = self._headers.strict_transport_security
        return response


class TenantResolutionMiddleware:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(self, request: Request, call_next: Any) -> Response:
        tenant_id = request.headers.get("x-tenant-id") or request.headers.get("x-organization-id")
        if tenant_id:
            request.state.tenant_id = tenant_id
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        path = request.url.path
        method = request.method
        status_code = str(response.status_code)
        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status_code=status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)
        return response
    
# app.py
from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app
from sentry_sdk.integrations.fastapi import FastApiIntegration
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from settings import get_settings
from database.connection import dispose_engine, init_engine
from task_queue.redis import close_redis_pool, init_redis_pool
from monitoring.logging import configure_logging
from monitoring.tracing import configure_tracing
from api.exceptions import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from api.middleware import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    TenantResolutionMiddleware,
)
from api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    configure_tracing(app, settings)
    app.state.db_engine = init_engine(settings)
    app.state.redis_pool = init_redis_pool(settings)
    app.state.start_time = time.time()
    try:
        import neuralcore_engine

        app.state.rust_engine = neuralcore_engine
    except ImportError:
        app.state.rust_engine = None
    try:
        yield
    finally:
        await dispose_engine(app.state.db_engine)
        await close_redis_pool(app.state.redis_pool)


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.logging.sentry_dsn is not None:
        sentry_sdk.init(
            dsn=settings.logging.sentry_dsn.get_secret_value(),
            environment=settings.environment.value,
            traces_sample_rate=settings.logging.sentry_traces_sample_rate,
            integrations=[FastApiIntegration()],
        )

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors.allow_origins,
        allow_methods=settings.app.cors.allow_methods,
        allow_headers=settings.app.cors.allow_headers,
        allow_credentials=settings.app.cors.allow_credentials,
        max_age=settings.app.cors.max_age,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(BaseHTTPMiddleware, dispatch=SecurityHeadersMiddleware(settings))
    app.add_middleware(BaseHTTPMiddleware, dispatch=TenantResolutionMiddleware(settings))
    app.add_middleware(BaseHTTPMiddleware, dispatch=RequestContextMiddleware(settings))

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(api_router, prefix=settings.api_prefix)

    if settings.monitoring.prometheus.enabled:
        app.mount(settings.monitoring.prometheus.path, make_asgi_app())

    if settings.monitoring.otlp.enabled:
        FastAPIInstrumentor.instrument_app(app)

    @app.get(settings.app.health_check.live_path, include_in_schema=False)
    async def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @app.get(settings.app.health_check.path, include_in_schema=False)
    async def health(request: Request) -> dict[str, object]:
        return {
            "status": "ok",
            "version": settings.version,
            "environment": settings.environment.value,
            "uptime_seconds": time.time() - request.app.state.start_time,
        }

    @app.get(settings.app.health_check.ready_path, include_in_schema=False)
    async def readiness(request: Request) -> ORJSONResponse:
        from monitoring.healthcheck import run_health_checks

        results = await run_health_checks(request.app, settings)
        healthy = all(result.healthy for result in results)
        status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return ORJSONResponse(
            status_code=status_code,
            content={
                "status": "ready" if healthy else "not_ready",
                "checks": {result.name: result.healthy for result in results},
            },
        )

    return app
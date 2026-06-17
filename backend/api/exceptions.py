# api/exceptions.py
from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str | None = None,
        detail: Any = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str | None = None) -> None:
        msg = f"{resource} not found" if not resource_id else f"{resource} '{resource_id}' not found"
        super().__init__(msg, status_code=status.HTTP_404_NOT_FOUND, error_code="NOT_FOUND")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, error_code="FORBIDDEN")


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, error_code="CONFLICT")


class UnprocessableError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, error_code="UNPROCESSABLE")


class QuotaError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS, error_code="QUOTA_EXCEEDED")


async def app_error_handler(request: Request, exc: AppError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "extra": exc.detail,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
    errors = [
        {"field": ".".join(str(loc) for loc in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed", "errors": errors},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    from monitoring.logging import get_logger
    logger = get_logger("neuralcore.api")
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

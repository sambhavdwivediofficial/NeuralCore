# monitoring/logging.py
from __future__ import annotations

import logging
import re
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog

from settings import Settings

_REDACTED = "***REDACTED***"
_compiled_patterns: list[re.Pattern[str]] = []


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        sanitized = value
        for pattern in _compiled_patterns:
            sanitized = pattern.sub(_REDACTED, sanitized)
        return sanitized
    if isinstance(value, dict):
        return {key: _sanitize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    return value


def _sanitize_processor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    if not _compiled_patterns:
        return event_dict
    return {key: _sanitize_value(value) for key, value in event_dict.items()}


def configure_logging(settings: Settings) -> None:
    global _compiled_patterns
    _compiled_patterns = [re.compile(pattern) for pattern in settings.logging.sanitize_patterns]

    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _sanitize_processor,
    ]

    if settings.logging.json_format:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    for module_name, module_level in settings.logging.per_module_levels.items():
        logging.getLogger(module_name).setLevel(getattr(logging, module_level.upper(), log_level))

    for noisy_logger in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)


@contextmanager
def log_slow_operation(operation: str, threshold_ms: float, **context: Any) -> Iterator[None]:
    logger = get_logger("neuralcore.performance")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms >= threshold_ms:
            logger.warning(
                "slow_operation",
                operation=operation,
                duration_ms=round(elapsed_ms, 2),
                threshold_ms=threshold_ms,
                **context,
            )


@contextmanager
def log_slow_query(settings: Settings, query_name: str, **context: Any) -> Iterator[None]:
    with log_slow_operation(f"db_query:{query_name}", settings.logging.slow_query_threshold_ms, **context):
        yield


@contextmanager
def log_slow_llm_call(settings: Settings, provider: str, model: str, **context: Any) -> Iterator[None]:
    with log_slow_operation(
        f"llm_call:{provider}:{model}",
        settings.logging.slow_llm_call_threshold_ms,
        provider=provider,
        model=model,
        **context,
    ):
        yield
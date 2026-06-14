# monitoring/healthcheck.py
from __future__ import annotations

import asyncio
import ctypes
import os
import shutil
import sys
import time
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text

from settings import Settings, VectorDBBackend


@dataclass(slots=True, frozen=True)
class HealthCheckResult:
    name: str
    healthy: bool
    detail: str = ""
    latency_ms: float = 0.0


async def run_health_checks(app: FastAPI, settings: Settings) -> list[HealthCheckResult]:
    targets = settings.monitoring.health_check_targets
    checks: list[Coroutine[Any, Any, HealthCheckResult]] = []
    if targets.database:
        checks.append(_check_database(app, settings))
    if targets.redis:
        checks.append(_check_redis(app, settings))
    if targets.vector_db:
        checks.append(_check_vector_db(settings))
    if targets.disk:
        checks.append(_check_disk(settings))
    if targets.memory:
        checks.append(_check_memory(settings))
    return list(await asyncio.gather(*checks))


async def _timed(name: str, coro: Coroutine[Any, Any, str]) -> HealthCheckResult:
    start = time.perf_counter()
    try:
        detail = await coro
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(name=name, healthy=True, detail=detail, latency_ms=round(latency_ms, 2))
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(name=name, healthy=False, detail=str(exc), latency_ms=round(latency_ms, 2))


async def _check_database(app: FastAPI, settings: Settings) -> HealthCheckResult:
    async def _run() -> str:
        engine = app.state.db_engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "connected"

    return await _timed("database", _run())


async def _check_redis(app: FastAPI, settings: Settings) -> HealthCheckResult:
    async def _run() -> str:
        pool = app.state.redis_pool
        client = Redis(connection_pool=pool)
        pong = await client.ping()
        return "pong" if pong else "no response"

    return await _timed("redis", _run())


async def _check_vector_db(settings: Settings) -> HealthCheckResult:
    backend = settings.vector_db.default

    async def _run() -> str:
        host, port = _vector_db_endpoint(settings, backend)
        if host is None:
            return f"{backend.value} is embedded, no network check required"
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
        writer.close()
        return f"{backend.value} reachable at {host}:{port}"

    return await _timed("vector_db", _run())


def _vector_db_endpoint(settings: Settings, backend: VectorDBBackend) -> tuple[str | None, int]:
    if backend == VectorDBBackend.QDRANT:
        config = settings.vector_db.qdrant
        return config.host, config.port
    if backend == VectorDBBackend.MILVUS:
        config = settings.vector_db.milvus
        return config.host, config.port
    if backend == VectorDBBackend.WEAVIATE:
        parsed = urlparse(settings.vector_db.weaviate.url)
        return parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
    if backend == VectorDBBackend.ELASTICSEARCH:
        parsed = urlparse(settings.vector_db.elasticsearch.hosts[0])
        return parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 9200)
    return None, 0


async def _check_disk(settings: Settings) -> HealthCheckResult:
    async def _run() -> str:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        used_percent = (usage.used / usage.total) * 100
        threshold = settings.monitoring.health_check_targets.disk_threshold_percent
        if used_percent >= threshold:
            raise RuntimeError(f"disk usage {used_percent:.1f}% exceeds threshold {threshold:.1f}%")
        return f"disk usage {used_percent:.1f}% of {usage.total // (1024 ** 3)} GB"

    return await _timed("disk", _run())


async def _check_memory(settings: Settings) -> HealthCheckResult:
    async def _run() -> str:
        used_percent = _memory_usage_percent()
        threshold = settings.monitoring.health_check_targets.memory_threshold_percent
        if used_percent is None:
            return "memory usage unavailable on this platform"
        if used_percent >= threshold:
            raise RuntimeError(f"memory usage {used_percent:.1f}% exceeds threshold {threshold:.1f}%")
        return f"memory usage {used_percent:.1f}%"

    return await _timed("memory", _run())


def _memory_usage_percent() -> float | None:
    if sys.platform.startswith("linux"):
        meminfo: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                key, _, value = line.partition(":")
                meminfo[key.strip()] = int(value.strip().split()[0])
        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", 0)
        if total == 0:
            return None
        return ((total - available) / total) * 100

    if sys.platform.startswith("win"):
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return None
        return float(stat.dwMemoryLoad)

    return None
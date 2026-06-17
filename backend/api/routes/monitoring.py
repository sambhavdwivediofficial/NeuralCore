# api/routes/monitoring.py
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from api.dependencies import CurrentUser, Pagination, get_app_settings
from settings import Settings

router = APIRouter()


@router.get("/health")
async def health_check(settings: Settings = Depends(get_app_settings)) -> dict[str, Any]:
    from monitoring.healthcheck import HealthCheckResult

    class _MockApp:
        class state:
            db_engine = None
            redis_pool = None

    checks = [
        {"name": "api", "healthy": True},
        {"name": "database", "healthy": False, "detail": "No DB engine (mock)"},
    ]
    return {"status": "degraded", "services": checks}


@router.get("/metrics")
async def overview_metrics(
    user: CurrentUser,
    range: Optional[str] = Query(default="7d"),
) -> dict[str, Any]:
    return {"range": range, "total_requests": 0, "error_rate": 0.0, "avg_latency_ms": 0.0, "active_agents": 0}


@router.get("/metrics/{service_name}")
async def service_metrics(service_name: str, user: CurrentUser, range: Optional[str] = Query(default="7d")) -> dict[str, Any]:
    return {"service": service_name, "range": range, "metrics": {}}


@router.get("/logs")
async def list_logs(
    user: CurrentUser,
    pagination: Pagination,
    search: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    return {"items": [], "total": 0, "page": pagination.page, "page_size": pagination.page_size}


@router.get("/logs/stream")
async def stream_logs(user: CurrentUser) -> StreamingResponse:
    async def _generator() -> AsyncIterator[str]:
        yield f"data: {json.dumps({'level': 'info', 'message': 'Log stream started', 'timestamp': __import__('time').time()})}\n\n"
        await asyncio.sleep(1.0)
        yield "data: [DONE]\n\n"

    return StreamingResponse(_generator(), media_type="text/event-stream")


@router.get("/traces")
async def list_traces(user: CurrentUser, page_size: int = Query(default=20)) -> list[dict[str, Any]]:
    return []


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, user: CurrentUser) -> dict[str, Any]:
    return {"trace_id": trace_id, "spans": [], "duration_ms": 0}


@router.get("/alerts")
async def list_alerts(
    user: CurrentUser,
    severity: Optional[str] = Query(default=None),
    alert_status: Optional[str] = Query(default=None, alias="status"),
) -> list[dict[str, Any]]:
    return []


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str, user: CurrentUser) -> dict[str, Any]:
    return {"id": alert_id, "name": "", "severity": "info", "status": "open", "message": ""}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: CurrentUser) -> dict[str, str]:
    return {"alert_id": alert_id, "status": "acknowledged"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: CurrentUser) -> dict[str, str]:
    return {"alert_id": alert_id, "status": "resolved"}


@router.get("/alert-rules")
async def list_alert_rules(user: CurrentUser) -> list[dict[str, Any]]:
    from monitoring.alerts import ALERT_RULES
    return [{"name": rule.name, "severity": rule.severity.value, "description": rule.description, "metric": rule.metric, "threshold": rule.threshold} for rule in ALERT_RULES]

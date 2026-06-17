# api/routes/ingestion.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings
from settings import Settings

router = APIRouter()


class IngestionJobRequest(BaseModel):
    knowledge_base_id: str
    source_type: str
    source_config: dict[str, Any]


@router.post("/knowledge-bases/{kb_id}/ingestion-sources", status_code=status.HTTP_202_ACCEPTED)
async def start_ingestion(
    kb_id: str,
    body: IngestionJobRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from task_queue.tasks.ingestion import process_ingestion_job
    task = process_ingestion_job.delay(kb_id, body.source_config)
    return {"job_id": task.id, "knowledge_base_id": kb_id, "source_type": body.source_type, "status": "queued"}

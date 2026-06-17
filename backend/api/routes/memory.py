# api/routes/memory.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Response, status

from api.dependencies import CurrentUser, get_app_settings, get_db, get_redis
from settings import Settings

router = APIRouter()


@router.get("/{agent_id}/memory")
async def get_agent_memory(
    agent_id: str,
    user: CurrentUser,
    db=Depends(get_db),
    redis=Depends(get_redis),
    settings: Settings = Depends(get_app_settings),
    layer: Optional[str] = Query(default=None),
) -> list[dict[str, Any]]:
    from sqlalchemy import text

    from database.connection import get_engine

    engine = get_engine()
    stmt = "SELECT id, layer, role, content, importance_score, access_count, created_at FROM agent_memories WHERE agent_id = :agent_id"
    params: dict[str, Any] = {"agent_id": agent_id}

    async with engine.connect() as conn:
        if layer:
            result = await conn.execute(
                text(stmt + " AND layer = :layer ORDER BY created_at DESC LIMIT 50"),
                {**params, "layer": layer},
            )
        else:
            result = await conn.execute(
                text(stmt + " ORDER BY created_at DESC LIMIT 50"),
                params,
            )
        rows = result.mappings().all()

    return [
        {
            "id": str(row["id"]),
            "layer": row["layer"],
            "role": row["role"],
            "content": row["content"],
            "importance_score": row["importance_score"],
            "access_count": row["access_count"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]


@router.delete(
    "/{agent_id}/memory/{layer}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def clear_agent_memory_layer(
    agent_id: str,
    layer: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> Response:
    from sqlalchemy import text

    from database.connection import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM agent_memories WHERE agent_id = :agent_id AND layer = :layer"),
            {"agent_id": agent_id, "layer": layer},
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

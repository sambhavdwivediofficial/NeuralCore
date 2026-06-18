# tools/builtin/memory.py
from __future__ import annotations

from typing import Any

from monitoring.logging import get_logger
from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

logger = get_logger("neuralcore.tools.memory")

MEMORY_READ_SCHEMA = ToolSchema(
    name="memory_read",
    description=(
        "Search and retrieve relevant memories from an agent's memory system. "
        "Searches across long-term, semantic, and episodic memory layers."
    ),
    parameters=[
        ToolParameter(name="query", type=ToolParameterType.STRING, description="Query to search memory for", required=True),
        ToolParameter(name="agent_id", type=ToolParameterType.STRING, description="UUID of the agent whose memory to search", required=True),
        ToolParameter(name="top_k", type=ToolParameterType.INTEGER, description="Number of memories to return (default: 5)", required=False, default=5),
        ToolParameter(name="layers", type=ToolParameterType.ARRAY, description="Memory layers to search: long_term, semantic, episodic (default: all)", required=False, default=["long_term", "semantic", "episodic"]),
    ],
    returns="array of {content, layer, importance_score}",
    category="memory",
)

MEMORY_WRITE_SCHEMA = ToolSchema(
    name="memory_write",
    description="Store a new memory in the agent's long-term memory with optional semantic embedding.",
    parameters=[
        ToolParameter(name="content", type=ToolParameterType.STRING, description="Content to store in memory", required=True),
        ToolParameter(name="agent_id", type=ToolParameterType.STRING, description="UUID of the agent", required=True),
        ToolParameter(name="importance_score", type=ToolParameterType.NUMBER, description="Importance score 0.0-1.0 (default: 0.5)", required=False, default=0.5),
        ToolParameter(name="role", type=ToolParameterType.STRING, description="Role label for the memory (e.g. 'assistant', 'user', 'system')", required=False, default="assistant"),
        ToolParameter(name="also_embed", type=ToolParameterType.BOOLEAN, description="Whether to embed the memory for semantic search (default: True)", required=False, default=True),
    ],
    returns="memory_id string",
    category="memory",
)


async def memory_read_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    import uuid
    from settings import get_settings
    from database.connection import get_session_factory
    from task_queue.redis import get_redis_client
    from memory.long_term import LongTermMemory
    from memory.semantic import SemanticMemory
    from memory.episodic import EpisodicMemory

    settings = get_settings()
    agent_id = uuid.UUID(arguments["agent_id"])
    query = arguments["query"]
    top_k = int(arguments.get("top_k", 5))
    layers = arguments.get("layers", ["long_term", "semantic", "episodic"])
    memories: list[dict[str, Any]] = []

    session_factory = get_session_factory()
    async with session_factory() as session:
        if "long_term" in layers:
            ltm = LongTermMemory(session, settings)
            entries = await ltm.retrieve(agent_id=agent_id, limit=top_k, min_importance=0.0)
            for entry in entries:
                memories.append({"content": entry.content, "layer": "long_term", "importance_score": entry.importance_score, "created_at": entry.created_at.isoformat()})

        if "episodic" in layers:
            ep = EpisodicMemory(session, settings)
            episodes = await ep.get_recent_episodes(agent_id=agent_id, limit=top_k)
            for episode in episodes:
                memories.append({"content": episode.content, "layer": "episodic", "importance_score": episode.importance_score, "created_at": episode.created_at.isoformat()})

    if "semantic" in layers:
        sem = SemanticMemory(settings)
        sem_results = await sem.search(agent_id=agent_id, query=query, top_k=top_k)
        for result in sem_results:
            memories.append({"content": result.content, "layer": "semantic", "importance_score": result.score, "metadata": result.metadata})

    memories.sort(key=lambda m: m.get("importance_score", 0.0), reverse=True)
    return {"query": query, "agent_id": str(agent_id), "memories": memories[:top_k], "total": len(memories)}


async def memory_write_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    import uuid
    from settings import get_settings
    from database.connection import get_session_factory

    settings = get_settings()
    agent_id = uuid.UUID(arguments["agent_id"])
    content = arguments["content"]
    importance = float(arguments.get("importance_score", 0.5))
    role = arguments.get("role", "assistant")
    also_embed = bool(arguments.get("also_embed", True))

    from memory.long_term import LongTermMemory
    from memory.semantic import SemanticMemory

    session_factory = get_session_factory()
    async with session_factory() as session:
        ltm = LongTermMemory(session, settings)
        entry = await ltm.store(agent_id=agent_id, content=content, role=role, importance_score=importance)
        await session.commit()

    if also_embed:
        sem = SemanticMemory(settings)
        await sem.store(agent_id=agent_id, memory_id=entry.id, content=content, metadata={"importance_score": importance, "role": role})

    return {"memory_id": entry.id, "agent_id": str(agent_id), "stored": True, "embedded": also_embed, "importance_score": importance}

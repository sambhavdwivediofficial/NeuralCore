# tools/builtin/retrieval.py
from __future__ import annotations

from typing import Any

from monitoring.logging import get_logger
from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

logger = get_logger("neuralcore.tools.retrieval")

RETRIEVAL_SCHEMA = ToolSchema(
    name="retrieval",
    description=(
        "Search a NeuralCore knowledge base using hybrid RAG retrieval (vector + BM25 + reranking). "
        "Returns the most relevant document chunks for the given query."
    ),
    parameters=[
        ToolParameter(name="query", type=ToolParameterType.STRING, description="Search query", required=True),
        ToolParameter(name="knowledge_base_id", type=ToolParameterType.STRING, description="UUID of the knowledge base to search", required=True),
        ToolParameter(name="top_k", type=ToolParameterType.INTEGER, description="Number of results to return (1-20, default: 5)", required=False, default=5),
        ToolParameter(name="use_reranking", type=ToolParameterType.BOOLEAN, description="Whether to apply reranking (default: True)", required=False, default=True),
        ToolParameter(name="use_graph", type=ToolParameterType.BOOLEAN, description="Whether to include graph-based retrieval (default: False)", required=False, default=False),
    ],
    returns="array of {id, score, text, metadata}",
    category="knowledge",
)


async def retrieval_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    import uuid
    from settings import get_settings
    from retrieval.retriever import Retriever

    settings = get_settings()
    retriever = Retriever(settings=settings)
    try:
        kb_id = uuid.UUID(arguments["knowledge_base_id"])
    except ValueError as exc:
        raise ValueError(f"Invalid knowledge_base_id UUID: {arguments['knowledge_base_id']}") from exc

    results = await retriever.search(
        knowledge_base_id=kb_id,
        query=arguments["query"],
        top_k=min(int(arguments.get("top_k", 5)), 20),
        use_hybrid=True,
        use_reranking=bool(arguments.get("use_reranking", True)),
        use_graph=bool(arguments.get("use_graph", False)),
    )

    return {
        "query": arguments["query"],
        "knowledge_base_id": str(kb_id),
        "results": [
            {
                "id": r.id,
                "score": round(r.score, 4),
                "rank": r.rank,
                "text": r.text or "",
                "metadata": r.metadata,
                "reranked": r.reranked,
            }
            for r in results
        ],
        "total": len(results),
    }

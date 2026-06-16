# retrieval/query_rewriter.py
from __future__ import annotations

import asyncio
from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.retrieval.query_rewriter")

_HYDE_PROMPT = """You are a document retrieval assistant. Given a user query, generate a hypothetical ideal document passage that would perfectly answer this query. Write only the passage, no explanations.

Query: {query}

Hypothetical passage:"""

_STEP_BACK_PROMPT = """Given the specific query below, generate a more general/abstract version of the question that captures the broader topic. Output only the rewritten question.

Original query: {query}

General question:"""

_DECOMPOSE_PROMPT = """Break down the following complex query into 2-4 simpler sub-questions that together would answer the original query. Output one sub-question per line, no numbering or bullets.

Query: {query}

Sub-questions:"""

_EXPAND_PROMPT = """Expand the following search query with relevant synonyms and related terms to improve search recall. Output only the expanded query.

Original query: {query}

Expanded query:"""


async def _call_llm(prompt: str, settings: Settings, max_tokens: int = 200) -> str:
    from model_gateway.provider_factory import get_model_gateway

    gateway = get_model_gateway(settings)
    request = CompletionRequest(
        messages=[ChatMessage(role=ChatRole.USER, content=prompt)],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    response = await gateway.chat_completion(request)
    return (response.content or "").strip()


async def rewrite_hyde(query: str, settings: Settings) -> str:
    if not settings.retrieval.query_rewriting.hyde_enabled:
        return query
    try:
        return await _call_llm(_HYDE_PROMPT.format(query=query), settings, max_tokens=300)
    except Exception:
        logger.warning("hyde_rewrite_failed", query=query[:100])
        return query


async def rewrite_step_back(query: str, settings: Settings) -> str:
    if not settings.retrieval.query_rewriting.step_back_enabled:
        return query
    try:
        return await _call_llm(_STEP_BACK_PROMPT.format(query=query), settings)
    except Exception:
        logger.warning("step_back_rewrite_failed", query=query[:100])
        return query


async def decompose_query(query: str, settings: Settings) -> list[str]:
    if not settings.retrieval.query_rewriting.decomposition_enabled:
        return [query]
    try:
        result = await _call_llm(_DECOMPOSE_PROMPT.format(query=query), settings, max_tokens=250)
        sub_queries = [line.strip() for line in result.splitlines() if line.strip()]
        return sub_queries[:4] if sub_queries else [query]
    except Exception:
        logger.warning("decompose_query_failed", query=query[:100])
        return [query]


async def expand_query(query: str, settings: Settings) -> str:
    if not settings.retrieval.query_rewriting.expansion_enabled:
        return query
    try:
        return await _call_llm(_EXPAND_PROMPT.format(query=query), settings)
    except Exception:
        logger.warning("expand_query_failed", query=query[:100])
        return query


async def rewrite_all_enabled(query: str, settings: Settings) -> dict[str, Any]:
    cfg = settings.retrieval.query_rewriting
    tasks: dict[str, Any] = {}
    rewrites: dict[str, Any] = {"original": query}

    async def _safe(key: str, coro: Any) -> None:
        try:
            rewrites[key] = await coro
        except Exception:
            rewrites[key] = query

    coroutines = []
    if cfg.hyde_enabled:
        coroutines.append(_safe("hyde", rewrite_hyde(query, settings)))
    if cfg.step_back_enabled:
        coroutines.append(_safe("step_back", rewrite_step_back(query, settings)))
    if cfg.expansion_enabled:
        coroutines.append(_safe("expanded", expand_query(query, settings)))
    if cfg.decomposition_enabled:
        coroutines.append(_safe("sub_queries", decompose_query(query, settings)))

    await asyncio.gather(*coroutines)
    return rewrites

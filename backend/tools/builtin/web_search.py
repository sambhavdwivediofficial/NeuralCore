# tools/builtin/web_search.py
from __future__ import annotations

from typing import Any

import httpx

from monitoring.logging import get_logger
from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

logger = get_logger("neuralcore.tools.web_search")

_DDGS_SEARCH_URL = "https://api.duckduckgo.com/"

WEB_SEARCH_SCHEMA = ToolSchema(
    name="web_search",
    description="Search the web for current information using DuckDuckGo. Returns titles, snippets, and URLs.",
    parameters=[
        ToolParameter(name="query", type=ToolParameterType.STRING, description="Search query string", required=True),
        ToolParameter(name="max_results", type=ToolParameterType.INTEGER, description="Maximum number of results to return (1-10, default: 5)", required=False, default=5),
        ToolParameter(name="region", type=ToolParameterType.STRING, description="Region code for results e.g. 'us-en', 'in-en' (default: wt-wt = worldwide)", required=False, default="wt-wt"),
    ],
    returns="array of {title, snippet, url}",
    category="information",
)


async def web_search_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments["query"]
    max_results = min(int(arguments.get("max_results", 5)), 10)
    region = arguments.get("region", "wt-wt")

    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        raw_results = list(ddgs.text(query, region=region, max_results=max_results))
        results = [
            {"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
            for r in raw_results
        ]
    except ImportError:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    _DDGS_SEARCH_URL,
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                    headers={"Accept": "application/json"},
                )
                data = response.json()
        except Exception as exc:
            logger.warning("web_search_http_fallback_failed", error=str(exc))
            return {"query": query, "results": [], "total": 0, "error": str(exc)}

        abstract = data.get("AbstractText", "")
        abstract_url = data.get("AbstractURL", "")
        results = []
        if abstract:
            results.append({"title": data.get("AbstractSource", query), "snippet": abstract, "url": abstract_url})

        for related in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(related, dict) and "Text" in related:
                results.append({"title": related.get("Text", "")[:80], "snippet": related.get("Text", ""), "url": related.get("FirstURL", "")})

    return {"query": query, "results": results[:max_results], "total": len(results)}

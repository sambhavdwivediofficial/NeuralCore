# tools/builtin/wikipedia.py
from __future__ import annotations

from typing import Any

import httpx

from monitoring.logging import get_logger
from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

logger = get_logger("neuralcore.tools.wikipedia")

_WIKIPEDIA_API_BASE = "https://{lang}.wikipedia.org/w/api.php"
_WIKIPEDIA_SUMMARY_BASE = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"

WIKIPEDIA_SEARCH_SCHEMA = ToolSchema(
    name="wikipedia_search",
    description=(
        "Search Wikipedia for factual, encyclopedic information about a topic, person, place, or concept. "
        "Best for established facts (history, science, biography, geography), not for breaking news or real-time data. "
        "Returns a summary with the article title, extract, and URL."
    ),
    parameters=[
        ToolParameter(name="query", type=ToolParameterType.STRING, description="Topic or search query", required=True),
        ToolParameter(name="language", type=ToolParameterType.STRING, description="Wikipedia language code (default: 'en')", required=False, default="en"),
        ToolParameter(name="sentences", type=ToolParameterType.INTEGER, description="Approximate number of sentences in the summary (default: 5)", required=False, default=5),
    ],
    returns="object with title, extract, url, thumbnail_url",
    category="information",
)


async def wikipedia_search_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments["query"]
    language = arguments.get("language", "en")
    sentences = int(arguments.get("sentences", 5))

    search_url = _WIKIPEDIA_API_BASE.format(lang=language)
    async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "NeuralCore-Agent/1.0"}) as client:
        search_response = await client.get(
            search_url,
            params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1},
        )
        search_data = search_response.json()
        results = search_data.get("query", {}).get("search", [])

        if not results:
            return {"query": query, "found": False, "message": f"No Wikipedia article found for '{query}'"}

        title = results[0]["title"]
        summary_url = _WIKIPEDIA_SUMMARY_BASE.format(lang=language, title=title.replace(" ", "_"))

        summary_response = await client.get(summary_url)
        if summary_response.status_code != 200:
            return {"query": query, "found": False, "message": f"Could not retrieve summary for '{title}'"}

        summary_data = summary_response.json()

    extract = summary_data.get("extract", "")
    extract_sentences = extract.split(". ")
    truncated_extract = ". ".join(extract_sentences[:sentences])
    if truncated_extract and not truncated_extract.endswith("."):
        truncated_extract += "."

    return {
        "query": query,
        "found": True,
        "title": summary_data.get("title", title),
        "extract": truncated_extract,
        "url": summary_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        "thumbnail_url": summary_data.get("thumbnail", {}).get("source"),
        "description": summary_data.get("description", ""),
    }


WIKIPEDIA_PAGE_CONTENT_SCHEMA = ToolSchema(
    name="wikipedia_get_full_page",
    description="Retrieve the full plain-text content of a specific Wikipedia article by exact title (use after wikipedia_search to get more detail).",
    parameters=[
        ToolParameter(name="title", type=ToolParameterType.STRING, description="Exact Wikipedia article title", required=True),
        ToolParameter(name="language", type=ToolParameterType.STRING, description="Wikipedia language code (default: 'en')", required=False, default="en"),
        ToolParameter(name="max_chars", type=ToolParameterType.INTEGER, description="Maximum characters to return (default: 5000)", required=False, default=5000),
    ],
    returns="object with title, content, url",
    category="information",
)


async def wikipedia_full_page_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    title = arguments["title"]
    language = arguments.get("language", "en")
    max_chars = int(arguments.get("max_chars", 5000))

    api_url = _WIKIPEDIA_API_BASE.format(lang=language)
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "NeuralCore-Agent/1.0"}) as client:
        response = await client.get(
            api_url,
            params={"action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "format": "json"},
        )
        data = response.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return {"title": title, "found": False}

    page = next(iter(pages.values()))
    if "missing" in page:
        return {"title": title, "found": False, "message": f"Wikipedia page '{title}' not found"}

    content = page.get("extract", "")
    truncated = content[:max_chars] + ("..." if len(content) > max_chars else "")

    return {
        "title": page.get("title", title),
        "found": True,
        "content": truncated,
        "url": f"https://{language}.wikipedia.org/wiki/{title.replace(' ', '_')}",
        "total_length": len(content),
        "truncated": len(content) > max_chars,
    }

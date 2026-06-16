# ingestion/website_loader.py
from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from ingestion.base_loader import BaseLoader, SourceNotFoundError, SourceType
from ingestion.loader_factory import register_loader

_MAX_CRAWL_DEPTH = 3
_MAX_PAGES = 50
_SKIP_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".xlsx", ".zip", ".tar", ".gz", ".png", ".jpg",
    ".jpeg", ".gif", ".svg", ".mp4", ".mp3", ".wav", ".ico", ".woff",
    ".woff2", ".ttf", ".eot", ".css", ".js", ".map",
})


def _same_domain(base_url: str, link_url: str) -> bool:
    return urlparse(base_url).netloc == urlparse(link_url).netloc


def _extract_links(html: str, base_url: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
            continue
        links.append(absolute.split("#")[0])
    return links


def _parse_page(html: str, url: str) -> tuple[str, str | None]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template", "header", "footer", "nav"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else None
    main = soup.find("main") or soup.find("article") or soup.find("body") or soup
    raw = main.get_text(separator="\n")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return "\n".join(lines), title


@register_loader(SourceType.WEBSITE)
class WebsiteLoader(BaseLoader):
    source_type = SourceType.WEBSITE

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        url: str = source_config["url"]
        max_depth: int = min(source_config.get("max_depth", 1), _MAX_CRAWL_DEPTH)
        max_pages: int = min(source_config.get("max_pages", 10), _MAX_PAGES)
        crawl: bool = source_config.get("crawl", False)
        timeout: float = source_config.get("timeout", 15.0)

        headers = {
            "User-Agent": "NeuralCore-Crawler/1.0 (+https://neuralcore.ai/bot)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en",
        }

        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(url, 0)]
        documents: list[dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            while queue and len(visited) < max_pages:
                current_url, depth = queue.pop(0)
                if current_url in visited:
                    continue
                visited.add(current_url)

                try:
                    response = await client.get(current_url)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        raise SourceNotFoundError(f"page not found: {current_url}", source_type=self.source_type.value) from exc
                    continue
                except httpx.TransportError:
                    continue

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue

                html = response.text
                text, title = _parse_page(html, current_url)
                if text.strip():
                    documents.append(
                        self._build_document(
                            text,
                            metadata={
                                "source_type": self.source_type.value,
                                "url": current_url,
                                "title": title,
                                "depth": depth,
                            },
                            source_id=current_url,
                        )
                    )

                if crawl and depth < max_depth:
                    links = _extract_links(html, current_url)
                    for link in links:
                        if link not in visited and _same_domain(url, link):
                            queue.append((link, depth + 1))

        return documents

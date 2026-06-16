# ingestion/sitemap_loader.py
from __future__ import annotations

import asyncio
from typing import Any
from xml.etree import ElementTree

import httpx

from ingestion.base_loader import BaseLoader, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader
from ingestion.website_loader import _parse_page

_SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "si": "http://www.sitemaps.org/schemas/sitemap-index/0.9",
}
_MAX_URLS = 200


def _extract_urls_from_sitemap(xml_text: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    tag = root.tag.split("}")[-1].lower()
    urls: list[str] = []

    if tag == "sitemapindex":
        for sitemap in root:
            loc = sitemap.find("sm:loc", _SITEMAP_NS) or sitemap.find("loc")
            if loc is not None and loc.text:
                urls.append(loc.text.strip())
    else:
        for url_element in root:
            loc = url_element.find("sm:loc", _SITEMAP_NS) or url_element.find("loc")
            if loc is not None and loc.text:
                urls.append(loc.text.strip())

    return urls


@register_loader(SourceType.SITEMAP)
class SitemapLoader(BaseLoader):
    source_type = SourceType.SITEMAP

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        sitemap_url: str = source_config["url"]
        max_urls: int = min(source_config.get("max_urls", 50), _MAX_URLS)
        timeout: float = source_config.get("timeout", 15.0)

        headers = {"User-Agent": "NeuralCore-Crawler/1.0 (+https://neuralcore.ai/bot)"}

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            try:
                response = await client.get(sitemap_url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise SourceConnectionError(str(exc), source_type=self.source_type.value) from exc

            page_urls = _extract_urls_from_sitemap(response.text)[:max_urls]

            if not page_urls:
                return []

            async def _fetch_page(url: str) -> dict[str, Any] | None:
                try:
                    page_response = await client.get(url)
                    page_response.raise_for_status()
                    content_type = page_response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        return None
                    text, title = _parse_page(page_response.text, url)
                    if not text.strip():
                        return None
                    return self._build_document(
                        text,
                        metadata={"source_type": self.source_type.value, "url": url, "title": title},
                        source_id=url,
                    )
                except (httpx.HTTPError, Exception):
                    return None

            tasks = [_fetch_page(url) for url in page_urls]
            results = await asyncio.gather(*tasks)

        return [doc for doc in results if doc is not None]

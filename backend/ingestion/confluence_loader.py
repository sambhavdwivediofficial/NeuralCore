# ingestion/confluence_loader.py
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader
from preprocessing.cleaner import CleaningOptions, clean_text

_CLEANING_OPTIONS = CleaningOptions(strip_html=True, decode_entities=True, remove_control_characters=True, normalize=True)


@register_loader(SourceType.CONFLUENCE)
class ConfluenceLoader(BaseLoader):
    source_type = SourceType.CONFLUENCE

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        base_url: str = source_config["base_url"].rstrip("/")
        username: str = source_config["username"]
        api_token: str = source_config["api_token"]
        space_key: str | None = source_config.get("space_key")
        page_ids: list[str] = source_config.get("page_ids", [])
        include_children: bool = source_config.get("include_children", True)
        limit: int = source_config.get("limit", 50)
        timeout: float = source_config.get("timeout", 30.0)

        api_base = f"{base_url}/wiki/rest/api"
        headers = {"Accept": "application/json"}
        auth = (username, api_token)

        async with httpx.AsyncClient(auth=auth, headers=headers, timeout=timeout) as client:
            async def _get(url: str, params: dict[str, Any] | None = None) -> Any:
                response = await client.get(url, params=params)
                if response.status_code == 401:
                    raise SourceAuthenticationError("invalid Confluence credentials", source_type=self.source_type.value)
                if response.status_code >= 400:
                    raise SourceConnectionError(f"Confluence API error {response.status_code}", source_type=self.source_type.value)
                return response.json()

            async def _fetch_page(page_id: str) -> dict[str, Any] | None:
                data = await _get(f"{api_base}/content/{page_id}", params={"expand": "body.storage,version,space,ancestors"})
                html_body = data.get("body", {}).get("storage", {}).get("value", "")
                text = clean_text(html_body, _CLEANING_OPTIONS)
                if not text.strip():
                    return None
                return self._build_document(
                    text,
                    metadata={
                        "source_type": self.source_type.value,
                        "page_id": page_id,
                        "title": data.get("title"),
                        "space": data.get("space", {}).get("key"),
                        "version": data.get("version", {}).get("number"),
                        "url": f"{base_url}/wiki{data.get('_links', {}).get('webui', '')}",
                    },
                    source_id=f"confluence:{page_id}",
                )

            if space_key and not page_ids:
                data = await _get(f"{api_base}/content", params={"spaceKey": space_key, "type": "page", "limit": limit, "expand": "version"})
                page_ids = [item["id"] for item in data.get("results", [])]

                if include_children:
                    child_ids: list[str] = []
                    for parent_id in page_ids:
                        children_data = await _get(f"{api_base}/content/{parent_id}/child/page", params={"limit": 50})
                        child_ids.extend(item["id"] for item in children_data.get("results", []))
                    page_ids = list(set(page_ids + child_ids))

            results = await asyncio.gather(*[_fetch_page(page_id) for page_id in page_ids], return_exceptions=True)

        return [doc for doc in results if isinstance(doc, dict) and doc is not None]
    
# ingestion/gitlab_loader.py
from __future__ import annotations

import asyncio
import base64
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceNotFoundError, SourceType
from ingestion.loader_factory import register_loader

_TEXT_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c",
    ".h", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".md", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bash",
    ".sql", ".html", ".css", ".scss", ".xml", ".dockerfile",
})


@register_loader(SourceType.GITLAB)
class GitlabLoader(BaseLoader):
    source_type = SourceType.GITLAB

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        project_id: str | int = source_config["project_id"]
        token: str = source_config["token"]
        branch: str = source_config.get("branch", "main")
        base_url: str = source_config.get("base_url", "https://gitlab.com")
        include_patterns: list[str] = source_config.get("include_patterns", [])
        exclude_patterns: list[str] = source_config.get("exclude_patterns", [])
        max_file_size_kb: int = source_config.get("max_file_size_kb", 500)
        timeout: float = source_config.get("timeout", 30.0)

        api_base = f"{base_url.rstrip('/')}/api/v4"
        encoded_id = quote(str(project_id), safe="")
        headers = {"PRIVATE-TOKEN": token, "Accept": "application/json"}

        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            async def _api_get(path: str) -> Any:
                response = await client.get(f"{api_base}{path}")
                if response.status_code == 401:
                    raise SourceAuthenticationError("invalid GitLab token", source_type=self.source_type.value)
                if response.status_code == 404:
                    raise SourceNotFoundError(f"not found: {path}", source_type=self.source_type.value)
                if response.status_code >= 400:
                    raise SourceConnectionError(f"GitLab API error {response.status_code}", source_type=self.source_type.value)
                return response.json()

            tree: list[dict[str, Any]] = []
            page = 1
            while True:
                batch = await _api_get(
                    f"/projects/{encoded_id}/repository/tree?ref={branch}&recursive=true&per_page=100&page={page}"
                )
                if not batch:
                    break
                tree.extend(item for item in batch if item.get("type") == "blob")
                if len(batch) < 100:
                    break
                page += 1

            filtered = [
                item for item in tree
                if PurePosixPath(item["path"]).suffix.lower() in _TEXT_EXTENSIONS
                and (not include_patterns or any(p in item["path"] for p in include_patterns))
                and not any(p in item["path"] for p in exclude_patterns)
            ]

            semaphore = asyncio.Semaphore(6)

            async def _fetch(item: dict[str, Any]) -> dict[str, Any] | None:
                async with semaphore:
                    try:
                        encoded_path = quote(item["path"], safe="")
                        data = await _api_get(f"/projects/{encoded_id}/repository/files/{encoded_path}?ref={branch}")
                        raw = base64.b64decode(data["content"].replace("\n", ""))
                        content = raw.decode("utf-8", errors="replace")
                        if len(raw) > max_file_size_kb * 1024 or not content.strip():
                            return None
                        return self._build_document(
                            content,
                            metadata={
                                "source_type": self.source_type.value,
                                "project_id": str(project_id),
                                "branch": branch,
                                "file_path": item["path"],
                                "file_extension": PurePosixPath(item["path"]).suffix.lower(),
                            },
                            source_id=f"gitlab:{project_id}/{branch}/{item['path']}",
                        )
                    except Exception:
                        return None

            results = await asyncio.gather(*[_fetch(item) for item in filtered])

        return [doc for doc in results if doc is not None]
    
# ingestion/bitbucket_loader.py
from __future__ import annotations

import asyncio
from pathlib import PurePosixPath
from typing import Any

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceNotFoundError, SourceType
from ingestion.loader_factory import register_loader

_BITBUCKET_API_BASE = "https://api.bitbucket.org/2.0"
_TEXT_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c",
    ".h", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".md", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".sql",
    ".html", ".css", ".scss", ".xml", ".dockerfile",
})


@register_loader(SourceType.BITBUCKET)
class BitbucketLoader(BaseLoader):
    source_type = SourceType.BITBUCKET

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        workspace: str = source_config["workspace"]
        repo_slug: str = source_config["repo_slug"]
        branch: str = source_config.get("branch", "main")
        username: str | None = source_config.get("username")
        app_password: str | None = source_config.get("app_password")
        include_patterns: list[str] = source_config.get("include_patterns", [])
        exclude_patterns: list[str] = source_config.get("exclude_patterns", [])
        max_file_size_kb: int = source_config.get("max_file_size_kb", 500)
        timeout: float = source_config.get("timeout", 30.0)

        auth = (username, app_password) if username and app_password else None

        async with httpx.AsyncClient(auth=auth, timeout=timeout) as client:
            async def _get(url: str) -> Any:
                response = await client.get(url)
                if response.status_code == 401:
                    raise SourceAuthenticationError("invalid Bitbucket credentials", source_type=self.source_type.value)
                if response.status_code == 404:
                    raise SourceNotFoundError(f"not found: {url}", source_type=self.source_type.value)
                if response.status_code >= 400:
                    raise SourceConnectionError(f"Bitbucket API error {response.status_code}", source_type=self.source_type.value)
                return response.json()

            paths: list[str] = []
            next_url: str | None = f"{_BITBUCKET_API_BASE}/repositories/{workspace}/{repo_slug}/src/{branch}/?pagelen=100"
            while next_url:
                data = await _get(next_url)
                for item in data.get("values", []):
                    if item.get("type") == "commit_file":
                        paths.append(item["path"])
                next_url = data.get("next")

            filtered = [
                path for path in paths
                if PurePosixPath(path).suffix.lower() in _TEXT_EXTENSIONS
                and (not include_patterns or any(p in path for p in include_patterns))
                and not any(p in path for p in exclude_patterns)
            ]

            semaphore = asyncio.Semaphore(6)

            async def _fetch(path: str) -> dict[str, Any] | None:
                async with semaphore:
                    try:
                        raw_url = f"{_BITBUCKET_API_BASE}/repositories/{workspace}/{repo_slug}/src/{branch}/{path}"
                        response = await client.get(raw_url)
                        if response.status_code != 200 or len(response.content) > max_file_size_kb * 1024:
                            return None
                        content = response.text.strip()
                        if not content:
                            return None
                        return self._build_document(
                            content,
                            metadata={
                                "source_type": self.source_type.value,
                                "workspace": workspace,
                                "repo_slug": repo_slug,
                                "branch": branch,
                                "file_path": path,
                                "file_extension": PurePosixPath(path).suffix.lower(),
                            },
                            source_id=f"bitbucket:{workspace}/{repo_slug}/{branch}/{path}",
                        )
                    except Exception:
                        return None

            results = await asyncio.gather(*[_fetch(path) for path in filtered])

        return [doc for doc in results if doc is not None]
    
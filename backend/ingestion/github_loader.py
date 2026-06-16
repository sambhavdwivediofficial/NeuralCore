# ingestion/github_loader.py
from __future__ import annotations

import asyncio
import base64
from pathlib import PurePosixPath
from typing import Any

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceNotFoundError, SourceType
from ingestion.loader_factory import register_loader

_GITHUB_API_BASE = "https://api.github.com"
_TEXT_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c",
    ".h", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".md", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bash",
    ".zsh", ".dockerfile", ".sql", ".html", ".css", ".scss", ".xml",
})


class _GitHubClient:
    def __init__(self, token: str | None, timeout: float) -> None:
        headers = {"Accept": "application/vnd.github.v3+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(base_url=_GITHUB_API_BASE, headers=headers, timeout=timeout)

    async def __aenter__(self) -> "_GitHubClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def get(self, path: str) -> Any:
        response = await self._client.get(path)
        if response.status_code == 401:
            raise SourceAuthenticationError("invalid or missing GitHub token", source_type="github")
        if response.status_code == 404:
            raise SourceNotFoundError(f"resource not found: {path}", source_type="github")
        if response.status_code >= 400:
            raise SourceConnectionError(f"GitHub API error {response.status_code}: {response.text}", source_type="github")
        return response.json()

    async def list_tree(self, owner: str, repo: str, branch: str) -> list[dict[str, Any]]:
        data = await self.get(f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        return [item for item in data.get("tree", []) if item.get("type") == "blob"]

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        data = await self.get(f"/repos/{owner}/{repo}/contents/{path}")
        raw = base64.b64decode(data["content"].replace("\n", ""))
        return raw.decode("utf-8", errors="replace")


@register_loader(SourceType.GITHUB)
class GithubLoader(BaseLoader):
    source_type = SourceType.GITHUB

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        owner: str = source_config["owner"]
        repo: str = source_config["repo"]
        branch: str = source_config.get("branch", "main")
        token: str | None = source_config.get("token")
        include_patterns: list[str] = source_config.get("include_patterns", [])
        exclude_patterns: list[str] = source_config.get("exclude_patterns", [])
        max_file_size_kb: int = source_config.get("max_file_size_kb", 500)
        timeout: float = source_config.get("timeout", 30.0)

        async with _GitHubClient(token, timeout) as client:
            tree = await client.list_tree(owner, repo, branch)

            filtered: list[dict[str, Any]] = []
            for item in tree:
                path = item["path"]
                size = item.get("size", 0)
                ext = PurePosixPath(path).suffix.lower()
                if ext not in _TEXT_EXTENSIONS:
                    continue
                if size > max_file_size_kb * 1024:
                    continue
                if include_patterns and not any(pattern in path for pattern in include_patterns):
                    continue
                if exclude_patterns and any(pattern in path for pattern in exclude_patterns):
                    continue
                filtered.append(item)

            semaphore = asyncio.Semaphore(8)

            async def _fetch(item: dict[str, Any]) -> dict[str, Any] | None:
                async with semaphore:
                    try:
                        content = await client.get_file_content(owner, repo, item["path"])
                        if not content.strip():
                            return None
                        return self._build_document(
                            content,
                            metadata={
                                "source_type": self.source_type.value,
                                "owner": owner,
                                "repo": repo,
                                "branch": branch,
                                "file_path": item["path"],
                                "file_extension": PurePosixPath(item["path"]).suffix.lower(),
                                "size_bytes": item.get("size", 0),
                            },
                            source_id=f"github:{owner}/{repo}/{branch}/{item['path']}",
                        )
                    except Exception:
                        return None

            results = await asyncio.gather(*[_fetch(item) for item in filtered])

        return [doc for doc in results if doc is not None]
    
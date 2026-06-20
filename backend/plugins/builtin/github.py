# plugins/builtin/github.py
from __future__ import annotations

from typing import Any

from plugins.plugin_loader import BasePlugin
from plugins.plugin_validator import PluginManifest, PluginPermission


class GitHubPlugin(BasePlugin):
    manifest = PluginManifest(
        id="github",
        name="GitHub",
        version="1.0.0",
        description="Connect GitHub repositories for code ingestion, issue tracking, and webhook-triggered re-indexing.",
        author="NeuralCore",
        entry_point="plugins.builtin.github:GitHubPlugin",
        permissions=[PluginPermission.READ_KNOWLEDGE_BASES, PluginPermission.WRITE_KNOWLEDGE_BASES, PluginPermission.NETWORK_ACCESS],
        category="developer_tools",
        config_schema={
            "type": "object",
            "properties": {"token": {"type": "string"}, "default_branch": {"type": "string", "default": "main"}},
            "required": ["token"],
        },
    )

    async def on_load(self) -> None:
        self.token = self.config.get("token")

    async def list_repositories(self, organization: str | None = None) -> list[dict[str, Any]]:
        import httpx
        url = f"https://api.github.com/orgs/{organization}/repos" if organization else "https://api.github.com/user/repos"
        async with httpx.AsyncClient(headers={"Authorization": f"Bearer {self.token}"}, timeout=15.0) as client:
            response = await client.get(url, params={"per_page": 100})
            response.raise_for_status()
            data = response.json()
        return [{"name": repo["name"], "full_name": repo["full_name"], "private": repo["private"], "default_branch": repo["default_branch"]} for repo in data]

    async def ingest_repository(self, owner: str, repo: str, knowledge_base_id: str) -> dict[str, Any]:
        from ingestion.github_loader import GithubLoader
        from settings import get_settings

        loader = GithubLoader(get_settings())
        documents = await loader.load({"owner": owner, "repo": repo, "branch": self.config.get("default_branch", "main"), "token": self.token})
        return {"owner": owner, "repo": repo, "knowledge_base_id": knowledge_base_id, "documents_found": len(documents)}

    async def register_webhook(self, owner: str, repo: str, webhook_url: str) -> dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(headers={"Authorization": f"Bearer {self.token}"}, timeout=15.0) as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/hooks",
                json={"name": "web", "active": True, "events": ["push"], "config": {"url": webhook_url, "content_type": "json"}},
            )
            response.raise_for_status()
            return response.json()

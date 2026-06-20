# plugins/builtin/jira.py
from __future__ import annotations

from typing import Any

from plugins.plugin_loader import BasePlugin
from plugins.plugin_validator import PluginManifest, PluginPermission


class JiraPlugin(BasePlugin):
    manifest = PluginManifest(
        id="jira",
        name="Jira",
        version="1.0.0",
        description="Connect Jira projects for issue ingestion, comment threading, and agent-driven ticket creation.",
        author="NeuralCore",
        entry_point="plugins.builtin.jira:JiraPlugin",
        permissions=[PluginPermission.READ_KNOWLEDGE_BASES, PluginPermission.WRITE_KNOWLEDGE_BASES, PluginPermission.NETWORK_ACCESS],
        category="project_management",
        config_schema={
            "type": "object",
            "properties": {"base_url": {"type": "string"}, "username": {"type": "string"}, "api_token": {"type": "string"}},
            "required": ["base_url", "username", "api_token"],
        },
    )

    async def on_load(self) -> None:
        self.base_url = self.config.get("base_url", "")
        self.username = self.config.get("username")
        self.api_token = self.config.get("api_token")

    async def ingest_project(self, project_key: str, knowledge_base_id: str) -> dict[str, Any]:
        from ingestion.jira_loader import JiraLoader
        from settings import get_settings

        loader = JiraLoader(get_settings())
        documents = await loader.load({
            "base_url": self.base_url, "username": self.username, "api_token": self.api_token,
            "project_keys": [project_key],
        })
        return {"project_key": project_key, "knowledge_base_id": knowledge_base_id, "documents_found": len(documents)}

    async def create_issue(self, project_key: str, summary: str, description: str, issue_type: str = "Task") -> dict[str, Any]:
        import httpx
        auth = (self.username, self.api_token)
        async with httpx.AsyncClient(auth=auth, timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/rest/api/3/issue",
                json={"fields": {"project": {"key": project_key}, "summary": summary, "description": description, "issuetype": {"name": issue_type}}},
            )
            response.raise_for_status()
            return response.json()

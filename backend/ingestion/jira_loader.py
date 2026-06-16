# ingestion/jira_loader.py
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader
from preprocessing.cleaner import CleaningOptions, clean_text

_CLEANING_OPTIONS = CleaningOptions(strip_html=True, decode_entities=True, normalize=True)


@register_loader(SourceType.JIRA)
class JiraLoader(BaseLoader):
    source_type = SourceType.JIRA

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        base_url: str = source_config["base_url"].rstrip("/")
        username: str = source_config["username"]
        api_token: str = source_config["api_token"]
        jql: str = source_config.get("jql", "")
        project_keys: list[str] = source_config.get("project_keys", [])
        max_results: int = source_config.get("max_results", 100)
        include_comments: bool = source_config.get("include_comments", True)
        timeout: float = source_config.get("timeout", 30.0)

        api_base = f"{base_url}/rest/api/3"
        auth = (username, api_token)
        headers = {"Accept": "application/json"}

        if not jql and project_keys:
            jql = f"project in ({', '.join(project_keys)}) ORDER BY updated DESC"
        elif not jql:
            jql = "ORDER BY updated DESC"

        async with httpx.AsyncClient(auth=auth, headers=headers, timeout=timeout) as client:
            async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
                response = await client.get(f"{api_base}{path}", params=params)
                if response.status_code == 401:
                    raise SourceAuthenticationError("invalid Jira credentials", source_type=self.source_type.value)
                if response.status_code >= 400:
                    raise SourceConnectionError(f"Jira API error {response.status_code}", source_type=self.source_type.value)
                return response.json()

            search_data = await _get("/search", params={"jql": jql, "maxResults": max_results, "fields": "summary,description,status,assignee,reporter,priority,labels,comment,created,updated,issuetype,project"})
            issues = search_data.get("issues", [])

            async def _build_issue_document(issue: dict[str, Any]) -> dict[str, Any]:
                fields = issue.get("fields", {})
                summary = fields.get("summary", "")
                description = fields.get("description") or ""
                if isinstance(description, dict):
                    description = clean_text(str(description), _CLEANING_OPTIONS)
                issue_text = f"# {issue['key']}: {summary}\n\n{description}"

                if include_comments:
                    comments = fields.get("comment", {}).get("comments", [])
                    if comments:
                        comment_lines = ["\n## Comments"]
                        for comment in comments:
                            author = comment.get("author", {}).get("displayName", "Unknown")
                            body = clean_text(str(comment.get("body", "")), _CLEANING_OPTIONS)
                            comment_lines.append(f"\n**{author}**: {body}")
                        issue_text += "\n".join(comment_lines)

                return self._build_document(
                    issue_text.strip(),
                    metadata={
                        "source_type": self.source_type.value,
                        "issue_key": issue["key"],
                        "issue_type": fields.get("issuetype", {}).get("name"),
                        "status": fields.get("status", {}).get("name"),
                        "priority": (fields.get("priority") or {}).get("name"),
                        "assignee": (fields.get("assignee") or {}).get("displayName"),
                        "reporter": (fields.get("reporter") or {}).get("displayName"),
                        "project": fields.get("project", {}).get("key"),
                        "labels": fields.get("labels", []),
                        "created": fields.get("created"),
                        "updated": fields.get("updated"),
                        "url": f"{base_url}/browse/{issue['key']}",
                    },
                    source_id=f"jira:{issue['key']}",
                )

            tasks = [_build_issue_document(issue) for issue in issues]
            results = await asyncio.gather(*tasks)

        return list(results)
    
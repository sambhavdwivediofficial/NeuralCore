# plugins/marketplace/registry.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.plugins.marketplace")


@dataclass(slots=True, frozen=True)
class MarketplaceListing:
    plugin_id: str
    name: str
    description: str
    author: str
    version: str
    category: str
    download_url: str
    icon_url: str | None = None
    rating: float = 0.0
    install_count: int = 0
    verified: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id, "name": self.name, "description": self.description,
            "author": self.author, "version": self.version, "category": self.category,
            "download_url": self.download_url, "icon_url": self.icon_url, "rating": self.rating,
            "install_count": self.install_count, "verified": self.verified, "tags": self.tags,
        }


_BUILTIN_MARKETPLACE_LISTINGS: list[MarketplaceListing] = [
    MarketplaceListing(plugin_id="github", name="GitHub", description="Code repository ingestion and webhook sync", author="NeuralCore", version="1.0.0", category="developer_tools", download_url="builtin://github", verified=True, tags=["code", "git", "ingestion"]),
    MarketplaceListing(plugin_id="slack", name="Slack", description="Channel ingestion and agent notifications", author="NeuralCore", version="1.0.0", category="communication", download_url="builtin://slack", verified=True, tags=["chat", "notifications"]),
    MarketplaceListing(plugin_id="notion", name="Notion", description="Page and database ingestion with markdown conversion", author="NeuralCore", version="1.0.0", category="productivity", download_url="builtin://notion", verified=True, tags=["docs", "wiki"]),
    MarketplaceListing(plugin_id="jira", name="Jira", description="Issue ingestion and ticket creation", author="NeuralCore", version="1.0.0", category="project_management", download_url="builtin://jira", verified=True, tags=["issues", "tickets"]),
]


class MarketplaceRegistry:
    def __init__(self) -> None:
        self._listings: dict[str, MarketplaceListing] = {listing.plugin_id: listing for listing in _BUILTIN_MARKETPLACE_LISTINGS}

    def search(self, query: str = "", category: str | None = None, verified_only: bool = False) -> list[MarketplaceListing]:
        results = list(self._listings.values())
        if query:
            query_lower = query.lower()
            results = [l for l in results if query_lower in l.name.lower() or query_lower in l.description.lower() or any(query_lower in tag for tag in l.tags)]
        if category:
            results = [l for l in results if l.category == category]
        if verified_only:
            results = [l for l in results if l.verified]
        return sorted(results, key=lambda l: l.install_count, reverse=True)

    def get_listing(self, plugin_id: str) -> MarketplaceListing | None:
        return self._listings.get(plugin_id)

    def list_categories(self) -> list[str]:
        return sorted({listing.category for listing in self._listings.values()})

    def increment_install_count(self, plugin_id: str) -> None:
        listing = self._listings.get(plugin_id)
        if listing is not None:
            self._listings[plugin_id] = MarketplaceListing(
                **{**listing.__dict__, "install_count": listing.install_count + 1}
            )


_global_marketplace: MarketplaceRegistry | None = None


def get_marketplace_registry() -> MarketplaceRegistry:
    global _global_marketplace
    if _global_marketplace is None:
        _global_marketplace = MarketplaceRegistry()
    return _global_marketplace

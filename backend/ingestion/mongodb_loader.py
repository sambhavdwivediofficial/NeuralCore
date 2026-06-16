# ingestion/mongodb_loader.py
from __future__ import annotations

import json
from typing import Any

from ingestion.base_loader import BaseLoader, LoaderError, SourceAuthenticationError, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader


def _doc_to_text(document: dict[str, Any], include_fields: list[str] | None, exclude_fields: list[str]) -> str:
    if include_fields:
        filtered = {key: document[key] for key in include_fields if key in document}
    else:
        filtered = {key: value for key, value in document.items() if key not in exclude_fields}

    lines: list[str] = []
    for key, value in filtered.items():
        if isinstance(value, dict):
            lines.append(f"{key}:\n" + "\n".join(f"  {k}: {v}" for k, v in value.items()))
        elif isinstance(value, list):
            lines.append(f"{key}: {', '.join(str(item) for item in value[:20])}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


@register_loader(SourceType.MONGODB)
class MongodbLoader(BaseLoader):
    source_type = SourceType.MONGODB

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        connection_string: str = source_config.get("connection_string", "mongodb://localhost:27017")
        database: str = source_config["database"]
        collection: str = source_config["collection"]
        query_filter: dict[str, Any] = source_config.get("filter", {})
        include_fields: list[str] | None = source_config.get("include_fields")
        exclude_fields: list[str] = source_config.get("exclude_fields", ["_id"])
        limit: int = source_config.get("limit", 1000)
        timeout: float = source_config.get("timeout", 30.0)

        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError as exc:
            raise LoaderError("motor is not installed; run: pip install motor", source_type=self.source_type.value) from exc

        try:
            client = AsyncIOMotorClient(connection_string, serverSelectionTimeoutMS=int(timeout * 1000))
            await client.admin.command("ping")
        except Exception as exc:
            message = str(exc)
            if "Authentication failed" in message:
                raise SourceAuthenticationError(message, source_type=self.source_type.value) from exc
            raise SourceConnectionError(message, source_type=self.source_type.value) from exc

        try:
            coll = client[database][collection]
            cursor = coll.find(query_filter).limit(limit)
            raw_docs = await cursor.to_list(length=limit)
        finally:
            client.close()

        documents: list[dict[str, Any]] = []
        for index, raw_doc in enumerate(raw_docs):
            doc_id = str(raw_doc.pop("_id", index))
            text = _doc_to_text(raw_doc, include_fields, exclude_fields)
            if not text.strip():
                continue
            documents.append(
                self._build_document(
                    text,
                    metadata={
                        "source_type": self.source_type.value,
                        "connection_host": connection_string.split("@")[-1].split("/")[0],
                        "database": database,
                        "collection": collection,
                        "document_id": doc_id,
                    },
                    source_id=f"mongodb:{database}/{collection}/{doc_id}",
                )
            )
        return documents
    
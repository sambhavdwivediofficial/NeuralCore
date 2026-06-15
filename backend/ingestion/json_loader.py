# ingestion/json_loader.py
from __future__ import annotations

import asyncio
import json
from typing import Any

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.JSON)
class JsonLoader(BaseLoader):
    source_type = SourceType.JSON

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        text_content = await self._read_text(source_config)
        data = await asyncio.to_thread(json.loads, text_content)
        source_id = source_config.get("file_path")
        records_path = source_config.get("records_path")

        records = self._resolve_records_path(data, records_path)

        if isinstance(records, list):
            documents: list[dict[str, Any]] = []
            for index, record in enumerate(records):
                documents.append(
                    self._build_document(
                        self._flatten_to_text(record),
                        metadata={"source_type": self.source_type.value, "file_path": source_id, "record_index": index},
                        source_id=f"{source_id}:{index}" if source_id else str(index),
                    )
                )
            return documents

        return [
            self._build_document(
                self._flatten_to_text(data),
                metadata={"source_type": self.source_type.value, "file_path": source_id},
                source_id=source_id,
            )
        ]

    @staticmethod
    def _resolve_records_path(data: Any, records_path: str | None) -> Any:
        if not records_path:
            return data
        current = data
        for key in records_path.split("."):
            if isinstance(current, dict):
                current = current.get(key, [])
            else:
                return []
        return current

    @staticmethod
    def _flatten_to_text(value: Any, prefix: str = "") -> str:
        if isinstance(value, dict):
            return "\n".join(
                JsonLoader._flatten_to_text(item, f"{prefix}.{key}" if prefix else str(key))
                for key, item in value.items()
            )
        if isinstance(value, list):
            return "\n".join(JsonLoader._flatten_to_text(item, f"{prefix}[{index}]") for index, item in enumerate(value))
        return f"{prefix}: {value}" if prefix else json.dumps(value, ensure_ascii=False)

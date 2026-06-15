# ingestion/txt_loader.py
from __future__ import annotations

from typing import Any

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.TXT)
class TxtLoader(BaseLoader):
    source_type = SourceType.TXT

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        encoding = source_config.get("encoding", "utf-8")
        text = await self._read_text(source_config, encoding=encoding)
        source_id = source_config.get("file_path")
        return [
            self._build_document(
                text.strip(),
                metadata={"source_type": self.source_type.value, "file_path": source_id, "encoding": encoding},
                source_id=source_id,
            )
        ]

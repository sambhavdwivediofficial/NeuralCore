# ingestion/csv_loader.py
from __future__ import annotations

import asyncio
import csv
import io
from typing import Any

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.CSV)
class CsvLoader(BaseLoader):
    source_type = SourceType.CSV

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        text_content = await self._read_text(source_config, encoding=source_config.get("encoding", "utf-8"))
        delimiter = source_config.get("delimiter", ",")
        row_as_document = source_config.get("row_as_document", True)
        source_id = source_config.get("file_path")

        rows, fieldnames = await asyncio.to_thread(self._parse_csv, text_content, delimiter)

        if row_as_document:
            documents: list[dict[str, Any]] = []
            for index, row in enumerate(rows):
                row_text = "\n".join(f"{key}: {value}" for key, value in row.items() if value not in (None, ""))
                if not row_text:
                    continue
                documents.append(
                    self._build_document(
                        row_text,
                        metadata={
                            "source_type": self.source_type.value,
                            "file_path": source_id,
                            "row_index": index,
                            "columns": fieldnames,
                        },
                        source_id=f"{source_id}:{index}" if source_id else str(index),
                    )
                )
            return documents

        table_text = "\n".join(", ".join(f"{key}={value}" for key, value in row.items()) for row in rows)
        return [
            self._build_document(
                table_text,
                metadata={"source_type": self.source_type.value, "file_path": source_id, "row_count": len(rows), "columns": fieldnames},
                source_id=source_id,
            )
        ]

    @staticmethod
    def _parse_csv(text_content: str, delimiter: str) -> tuple[list[dict[str, str]], list[str]]:
        reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])

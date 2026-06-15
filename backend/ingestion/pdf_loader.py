# ingestion/pdf_loader.py
from __future__ import annotations

import asyncio
import io
from typing import Any

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.PDF)
class PdfLoader(BaseLoader):
    source_type = SourceType.PDF

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        raw_bytes = await self._read_bytes(source_config)
        return await asyncio.to_thread(self._parse_pdf, raw_bytes, source_config)

    def _parse_pdf(self, raw_bytes: bytes, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw_bytes))
        source_id = source_config.get("file_path")
        page_as_document = source_config.get("page_as_document", False)
        info = reader.metadata or {}

        base_metadata = {
            "source_type": self.source_type.value,
            "file_path": source_id,
            "page_count": len(reader.pages),
            "title": info.get("/Title"),
            "author": info.get("/Author"),
        }

        if page_as_document:
            documents: list[dict[str, Any]] = []
            for index, page in enumerate(reader.pages):
                page_text = (page.extract_text() or "").strip()
                if not page_text:
                    continue
                documents.append(
                    self._build_document(
                        page_text,
                        metadata={**base_metadata, "page_number": index + 1},
                        source_id=f"{source_id}:page_{index + 1}" if source_id else f"page_{index + 1}",
                    )
                )
            return documents

        full_text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
        return [self._build_document(full_text, metadata=base_metadata, source_id=source_id)]

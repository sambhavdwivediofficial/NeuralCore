# ingestion/xml_loader.py
from __future__ import annotations

import asyncio
from typing import Any
from xml.etree import ElementTree

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.XML)
class XmlLoader(BaseLoader):
    source_type = SourceType.XML

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        text_content = await self._read_text(source_config)
        root = await asyncio.to_thread(ElementTree.fromstring, text_content)
        flattened = self._flatten_element(root)
        source_id = source_config.get("file_path")
        return [
            self._build_document(
                flattened,
                metadata={"source_type": self.source_type.value, "file_path": source_id, "root_tag": root.tag},
                source_id=source_id,
            )
        ]

    @staticmethod
    def _flatten_element(element: ElementTree.Element, depth: int = 0) -> str:
        indent = "  " * depth
        attrs = " ".join(f'{key}="{value}"' for key, value in element.attrib.items())
        tag = element.tag.split("}")[-1]
        line = f"{indent}{tag}" + (f" ({attrs})" if attrs else "")
        if element.text and element.text.strip():
            line += f": {element.text.strip()}"

        children = [XmlLoader._flatten_element(child, depth + 1) for child in element]
        return "\n".join([line, *children])

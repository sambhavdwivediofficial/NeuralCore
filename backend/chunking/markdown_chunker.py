# chunking/markdown_chunker.py
from __future__ import annotations

import re

from chunking.base_chunker import BaseChunker, count_tokens, recursive_split_text, register_chunker
from database.models.knowledgebase import ChunkingStrategy

HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")

_FALLBACK_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " ", ""]


@register_chunker(ChunkingStrategy.MARKDOWN)
class MarkdownChunker(BaseChunker):
    def split(self, text: str) -> list[str]:
        sections = self._split_by_headers(text)
        chunks: list[str] = []

        for header_path, content in sections:
            content = content.strip()
            if not content:
                continue

            prefix = (" > ".join(header_path) + "\n\n") if header_path else ""
            combined = (prefix + content).strip()
            if count_tokens(combined) <= self.chunk_size:
                chunks.append(combined)
                continue

            budget = max(self.chunk_size - count_tokens(prefix), 1)
            for sub_chunk in recursive_split_text(content, _FALLBACK_SEPARATORS, budget, self.chunk_overlap):
                chunks.append((prefix + sub_chunk).strip() if prefix else sub_chunk)

        return chunks

    @staticmethod
    def _split_by_headers(text: str) -> list[tuple[list[str], str]]:
        lines = text.splitlines()
        sections: list[tuple[list[str], str]] = []
        stack: list[tuple[int, str]] = []
        buffer: list[str] = []

        def flush() -> None:
            content = "\n".join(buffer).strip()
            if content:
                sections.append(([title for _, title in stack], content))
            buffer.clear()

        for line in lines:
            match = HEADER_PATTERN.match(line)
            if match:
                flush()
                level = len(match.group(1))
                title = match.group(2).strip()
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
            else:
                buffer.append(line)

        flush()
        if not sections:
            sections.append(([], text))
        return sections
    
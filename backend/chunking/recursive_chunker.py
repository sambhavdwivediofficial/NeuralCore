# chunking/recursive_chunker.py
from __future__ import annotations

from chunking.base_chunker import BaseChunker, recursive_split_text, register_chunker
from database.models.knowledgebase import ChunkingStrategy

DEFAULT_SEPARATORS: list[str] = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]


@register_chunker(ChunkingStrategy.RECURSIVE)
class RecursiveChunker(BaseChunker):
    separators: list[str] = DEFAULT_SEPARATORS

    def split(self, text: str) -> list[str]:
        return recursive_split_text(text, list(self.separators), self.chunk_size, self.chunk_overlap)
    
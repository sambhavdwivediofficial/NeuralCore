# chunking/token_chunker.py
from __future__ import annotations

from chunking.base_chunker import BaseChunker, decode_tokens, encode_tokens, register_chunker
from database.models.knowledgebase import ChunkingStrategy


@register_chunker(ChunkingStrategy.TOKEN)
class TokenChunker(BaseChunker):
    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        tokens = encode_tokens(text)
        if len(tokens) <= self.chunk_size:
            return [text]

        step = max(self.chunk_size - self.chunk_overlap, 1)
        chunks: list[str] = []
        for start in range(0, len(tokens), step):
            window = tokens[start : start + self.chunk_size]
            chunk_text = decode_tokens(window).strip()
            if chunk_text:
                chunks.append(chunk_text)
            if start + self.chunk_size >= len(tokens):
                break
        return chunks
    
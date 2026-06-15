# chunking/code_chunker.py
from __future__ import annotations

from chunking.base_chunker import BaseChunker, recursive_split_text, register_chunker
from database.models.knowledgebase import ChunkingStrategy

CODE_SEPARATORS: list[str] = [
    "\nclass ",
    "\ndef ",
    "\nasync def ",
    "\nfunction ",
    "\nasync function ",
    "\nexport ",
    "\n\n",
    "\n",
    " ",
    "",
]


@register_chunker(ChunkingStrategy.CODE)
class CodeChunker(BaseChunker):
    separators: list[str] = CODE_SEPARATORS

    def split(self, text: str) -> list[str]:
        return recursive_split_text(text, list(self.separators), self.chunk_size, self.chunk_overlap)
    
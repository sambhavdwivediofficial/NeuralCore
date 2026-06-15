# chunking/hybrid_chunker.py
from __future__ import annotations

import ast

from chunking.ast_chunker import ASTChunker
from chunking.base_chunker import BaseChunker, count_tokens, register_chunker
from chunking.code_chunker import CodeChunker
from chunking.markdown_chunker import HEADER_PATTERN, MarkdownChunker
from chunking.recursive_chunker import RecursiveChunker
from chunking.semantic_chunker import SemanticChunker
from database.models.knowledgebase import ChunkingStrategy

_CODE_INDICATORS: tuple[str, ...] = (
    "{", "}", ";", "function ", "class ", "def ", "import ", "const ", "let ", "var ", "=>", "#include",
)


@register_chunker(ChunkingStrategy.HYBRID)
class HybridChunker(BaseChunker):
    def split(self, text: str) -> list[str]:
        stripped = text.strip()
        if not stripped:
            return []

        if HEADER_PATTERN.search(stripped):
            return MarkdownChunker(self.chunk_size, self.chunk_overlap).split(stripped)

        if self._looks_like_python(stripped):
            chunks = ASTChunker(self.chunk_size, self.chunk_overlap).split(stripped)
            if chunks:
                return chunks

        if self._looks_like_code(stripped):
            return CodeChunker(self.chunk_size, self.chunk_overlap).split(stripped)

        if count_tokens(stripped) > self.chunk_size * 3:
            return RecursiveChunker(self.chunk_size, self.chunk_overlap).split(stripped)

        return SemanticChunker(self.chunk_size, self.chunk_overlap).split(stripped)

    @staticmethod
    def _looks_like_python(text: str) -> bool:
        try:
            ast.parse(text)
            return True
        except SyntaxError:
            return False

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return False
        hits = sum(1 for line in lines if any(indicator in line for indicator in _CODE_INDICATORS))
        return (hits / len(lines)) > 0.2
    
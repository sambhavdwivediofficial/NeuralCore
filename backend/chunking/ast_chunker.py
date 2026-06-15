# chunking/ast_chunker.py
from __future__ import annotations

import ast

from chunking.base_chunker import BaseChunker, count_tokens, recursive_split_text, register_chunker
from database.models.knowledgebase import ChunkingStrategy

_FALLBACK_SEPARATORS: list[str] = ["\n\n", "\n", " ", ""]


@register_chunker(ChunkingStrategy.AST)
class ASTChunker(BaseChunker):
    def split(self, text: str) -> list[str]:
        stripped = text.strip()
        if not stripped:
            return []

        try:
            tree = ast.parse(stripped)
        except SyntaxError:
            return recursive_split_text(stripped, _FALLBACK_SEPARATORS, self.chunk_size, self.chunk_overlap)

        lines = stripped.splitlines(keepends=True)
        segments: list[str] = []
        cursor = 0

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.l
                
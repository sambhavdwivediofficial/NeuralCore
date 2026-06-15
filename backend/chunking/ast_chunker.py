# chunking/ast_chunker.py
from __future__ import annotations

import ast

from chunking.base_chunker import BaseChunker, count_tokens, recursive_split_text, register_chunker
from database.models.knowledgebase import ChunkingStrategy

_FALLBACK_SEPARATORS: list[str] = ["\n\n", "\n", " ", ""]
_DEFINITION_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _effective_start_line(node: ast.AST) -> int:
    decorators = getattr(node, "decorator_list", None)
    if decorators:
        return min(decorator.lineno for decorator in decorators)
    return getattr(node, "lineno", 1)


def _extract_lines(source_lines: list[str], start_line: int, end_line: int) -> str:
    if start_line < 1 or end_line < start_line:
        return ""
    return "\n".join(source_lines[start_line - 1 : end_line]).strip()


@register_chunker(ChunkingStrategy.AST)
class ASTChunker(BaseChunker):
    def split(self, text: str) -> list[str]:
        source = text.strip("\n")
        if not source.strip():
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return recursive_split_text(source, _FALLBACK_SEPARATORS, self.chunk_size, self.chunk_overlap)

        segments = self._extract_top_level_segments(tree, source)
        if not segments:
            return recursive_split_text(source, _FALLBACK_SEPARATORS, self.chunk_size, self.chunk_overlap)

        chunks: list[str] = []
        for segment, node in segments:
            chunks.extend(self._finalize_segment(segment, node))
        return chunks

    @staticmethod
    def _extract_top_level_segments(tree: ast.Module, source: str) -> list[tuple[str, ast.AST | None]]:
        lines = source.splitlines()
        total_lines = len(lines)
        segments: list[tuple[str, ast.AST | None]] = []
        cursor = 1

        for node in tree.body:
            start_line = _effective_start_line(node)
            end_line = getattr(node, "end_lineno", start_line)

            if start_line > cursor:
                leading = _extract_lines(lines, cursor, start_line - 1)
                if leading:
                    segments.append((leading, None))

            segment = _extract_lines(lines, start_line, end_line)
            if segment:
                node_for_split = node if isinstance(node, _DEFINITION_TYPES) else None
                segments.append((segment, node_for_split))

            cursor = end_line + 1

        if cursor <= total_lines:
            trailing = _extract_lines(lines, cursor, total_lines)
            if trailing:
                segments.append((trailing, None))

        return segments

    def _finalize_segment(self, segment: str, node: ast.AST | None) -> list[str]:
        if count_tokens(segment) <= self.chunk_size:
            return [segment]

        if isinstance(node, ast.ClassDef):
            class_chunks = self._split_class(segment)
            if class_chunks:
                return class_chunks

        return recursive_split_text(segment, _FALLBACK_SEPARATORS, self.chunk_size, self.chunk_overlap)

    def _split_class(self, segment: str) -> list[str]:
        try:
            class_node = ast.parse(segment).body[0]
        except (SyntaxError, IndexError):
            return []

        if not isinstance(class_node, ast.ClassDef) or not class_node.body:
            return []

        lines = segment.splitlines()
        header_end = _effective_start_line(class_node.body[0]) - 1
        header = _extract_lines(lines, 1, header_end)

        chunks: list[str] = []
        for member in class_node.body:
            start_line = _effective_start_line(member)
            end_line = getattr(member, "end_lineno", start_line)
            member_source = _extract_lines(lines, start_line, end_line)
            if not member_source:
                continue

            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = f"{header}\n    ...\n\n" if header else ""
                combined = f"{prefix}{member_source}"
                if count_tokens(combined) <= self.chunk_size:
                    chunks.append(combined.strip())
                else:
                    for piece in recursive_split_text(member_source, _FALLBACK_SEPARATORS, self.chunk_size, self.chunk_overlap):
                        chunks.append((prefix + piece).strip())
            else:
                combined = f"{header}\n{member_source}" if header else member_source
                chunks.append(combined.strip())

        return chunks
    
# chunking/semantic_chunker.py
from __future__ import annotations

import re

from chunking.base_chunker import (
    BaseChunker,
    apply_overlap,
    count_tokens,
    recursive_split_text,
    register_chunker,
    split_sentences,
)
from database.models.knowledgebase import ChunkingStrategy

_FALLBACK_SEPARATORS: list[str] = ["\n\n", "\n", " ", ""]
_WORD_PATTERN = re.compile(r"\w+")


@register_chunker(ChunkingStrategy.SEMANTIC)
class SemanticChunker(BaseChunker):
    similarity_drop_threshold: float = 0.35

    def split(self, text: str) -> list[str]:
        sentences = split_sentences(text)
        if not sentences:
            return []
        if len(sentences) == 1:
            return recursive_split_text(sentences[0], _FALLBACK_SEPARATORS, self.chunk_size, self.chunk_overlap)

        similarities = [self._similarity(sentences[i], sentences[i + 1]) for i in range(len(sentences) - 1)]
        breakpoints = self._find_breakpoints(similarities)

        groups: list[list[str]] = [[sentences[0]]]
        for index in range(1, len(sentences)):
            if (index - 1) in breakpoints:
                groups.append([sentences[index]])
            else:
                groups[-1].append(sentences[index])

        chunks: list[str] = []
        for group in groups:
            group_text = " ".join(group)
            if count_tokens(group_text) <= self.chunk_size:
                chunks.append(group_text)
            else:
                chunks.extend(recursive_split_text(group_text, _FALLBACK_SEPARATORS, self.chunk_size, self.chunk_overlap))

        return apply_overlap(chunks, self.chunk_overlap, " ")

    @staticmethod
    def _similarity(first: str, second: str) -> float:
        words_a = set(_WORD_PATTERN.findall(first.lower()))
        words_b = set(_WORD_PATTERN.findall(second.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union else 0.0

    def _find_breakpoints(self, similarities: list[float]) -> set[int]:
        if not similarities:
            return set()
        average = sum(similarities) / len(similarities)
        return {index for index, value in enumerate(similarities) if average - value >= self.similarity_drop_threshold}
    
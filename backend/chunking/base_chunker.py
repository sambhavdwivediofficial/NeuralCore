# chunking/base_chunker.py
from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod

from database.models.knowledgebase import ChunkingStrategy

try:
    import neuralcore_engine
except ImportError:
    neuralcore_engine = None

try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")
except ImportError:
    tiktoken = None
    _ENCODING = None

_SENTENCE_PATTERN = re.compile(r"(?<=[.!?。！？])\s+")


def count_tokens(text: str) -> int:
    if neuralcore_engine is not None:
        func = getattr(neuralcore_engine, "py_count_tokens_approximate", None)
        if func is not None:
            try:
                return int(func(text))
            except Exception:
                pass
    if _ENCODING is not None:
        return len(_ENCODING.encode(text))
    return max(1, math.ceil(len(text) / 4))


def encode_tokens(text: str) -> list[int]:
    if _ENCODING is not None:
        return _ENCODING.encode(text)
    return list(text.encode("utf-8"))


def decode_tokens(tokens: list[int]) -> str:
    if _ENCODING is not None:
        return _ENCODING.decode(tokens)
    return bytes(tokens).decode("utf-8", errors="ignore")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    sentences = [sentence.strip() for sentence in _SENTENCE_PATTERN.split(text) if sentence.strip()]
    return sentences or [text]


class BaseChunker(ABC):
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = max(chunk_size, 1)
        self.chunk_overlap = min(max(chunk_overlap, 0), max(self.chunk_size - 1, 0))

    @abstractmethod
    def split(self, text: str) -> list[str]: ...


class CharacterChunker(BaseChunker):
    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        char_size = self.chunk_size * 4
        char_overlap = self.chunk_overlap * 4
        step = max(char_size - char_overlap, 1)
        return [chunk.strip() for i in range(0, len(text), step) if (chunk := text[i : i + char_size]).strip()]


def _apply_overlap(chunks: list[str], chunk_overlap: int, separator: str) -> list[str]:
    if chunk_overlap <= 0 or len(chunks) <= 1:
        return chunks
    overlapped = [chunks[0]]
    for index in range(1, len(chunks)):
        previous_tokens = encode_tokens(chunks[index - 1])
        overlap_text = decode_tokens(previous_tokens[-chunk_overlap:])
        overlapped.append(f"{overlap_text}{separator}{chunks[index]}".strip())
    return overlapped


def recursive_split_text(text: str, separators: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if count_tokens(text) <= chunk_size:
        return [text]

    separator = separators[0] if separators else ""
    remaining_separators = separators[1:]

    if not separator:
        tokens = encode_tokens(text)
        step = max(chunk_size - chunk_overlap, 1)
        return [
            chunk
            for i in range(0, len(tokens), step)
            if (chunk := decode_tokens(tokens[i : i + chunk_size]).strip())
        ]

    parts = [part for part in text.split(separator) if part.strip()]
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = f"{current}{separator}{part}" if current else part
        if count_tokens(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current.strip())
        if count_tokens(part) > chunk_size:
            chunks.extend(recursive_split_text(part, remaining_separators, chunk_size, chunk_overlap))
            current = ""
        else:
            current = part

    if current.strip():
        chunks.append(current.strip())

    return _apply_overlap(chunks, chunk_overlap, separator)


_CHUNKER_REGISTRY: dict[ChunkingStrategy, type[BaseChunker]] = {ChunkingStrategy.CHARACTER: CharacterChunker}


def register_chunker(strategy: ChunkingStrategy):
    def decorator(cls: type[BaseChunker]) -> type[BaseChunker]:
        _CHUNKER_REGISTRY[strategy] = cls
        return cls

    return decorator


def get_chunker(strategy: ChunkingStrategy | str, chunk_size: int = 512, chunk_overlap: int = 50) -> BaseChunker:
    if isinstance(strategy, str):
        strategy = ChunkingStrategy(strategy)

    if strategy not in _CHUNKER_REGISTRY:
        from chunking import (  # noqa: F401
            ast_chunker,
            code_chunker,
            hybrid_chunker,
            markdown_chunker,
            recursive_chunker,
            semantic_chunker,
            token_chunker,
        )

    chunker_class = _CHUNKER_REGISTRY.get(strategy, _CHUNKER_REGISTRY[ChunkingStrategy.CHARACTER])
    return chunker_class(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

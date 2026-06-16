# retrieval/bm25.py
from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.retrieval.bm25")

_TOKEN_PATTERN = re.compile(r"\b\w+\b")
_PORTER_SUFFIX_RULES: list[tuple[str, str, int]] = [
    ("sses", "ss", 0), ("ies", "i", 0), ("ss", "ss", 0), ("s", "", 0),
    ("eed", "ee", 5), ("ed", "", 5), ("ing", "", 5),
    ("ational", "ate", 0), ("tional", "tion", 0), ("enci", "ence", 0),
    ("anci", "ance", 0), ("izer", "ize", 0), ("alli", "al", 0),
    ("entli", "ent", 0), ("eli", "e", 0), ("ousli", "ous", 0),
    ("ization", "ize", 0), ("ation", "ate", 0), ("ator", "ate", 0),
    ("ical", "ic", 0), ("ness", "", 0), ("ful", "", 0), ("ment", "", 0),
    ("ism", "", 0), ("ous", "", 0), ("ive", "", 0), ("ize", "", 0),
]
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "no",
    "this", "that", "these", "those", "it", "its", "they", "their",
})


def _porter_stem(word: str) -> str:
    if len(word) <= 3:
        return word
    for suffix, replacement, min_remaining in _PORTER_SUFFIX_RULES:
        if word.endswith(suffix) and len(word) - len(suffix) >= min_remaining:
            return word[: -len(suffix)] + replacement
    return word


def _tokenize(text: str, use_stemmer: bool = True) -> list[str]:
    tokens = _TOKEN_PATTERN.findall(text.lower())
    filtered = [token for token in tokens if token not in _STOPWORDS and len(token) > 1]
    if use_stemmer:
        return [_porter_stem(token) for token in filtered]
    return filtered


@dataclass
class BM25Document:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    _tokens: list[str] = field(default_factory=list, repr=False)
    _tf: dict[str, float] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._tokens = _tokenize(self.text)
        counts = Counter(self._tokens)
        total = len(self._tokens)
        self._tf = {token: count / total for token, count in counts.items()} if total else {}


@dataclass
class BM25SearchResult:
    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._documents: dict[str, BM25Document] = {}
        self._df: dict[str, int] = {}
        self._avg_doc_len: float = 0.0
        self._idf: dict[str, float] = {}
        self._dirty: bool = False

    def add(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        doc = BM25Document(id=doc_id, text=text, metadata=metadata or {})
        self._documents[doc_id] = doc
        for token in set(doc._tokens):
            self._df[token] = self._df.get(token, 0) + 1
        self._dirty = True

    def add_batch(self, documents: list[dict[str, Any]]) -> None:
        for document in documents:
            self.add(document["id"], document["text"], document.get("metadata"))

    def remove(self, doc_id: str) -> None:
        doc = self._documents.pop(doc_id, None)
        if doc is None:
            return
        for token in set(doc._tokens):
            if token in self._df:
                self._df[token] = max(0, self._df[token] - 1)
                if self._df[token] == 0:
                    del self._df[token]
        self._dirty = True

    def _rebuild_idf(self) -> None:
        n = len(self._documents)
        if n == 0:
            self._idf = {}
            self._avg_doc_len = 0.0
            return
        self._avg_doc_len = sum(len(doc._tokens) for doc in self._documents.values()) / n
        self._idf = {
            token: math.log((n - df + 0.5) / (df + 0.5) + 1)
            for token, df in self._df.items()
        }
        self._dirty = False

    def search(self, query: str, top_k: int = 10) -> list[BM25SearchResult]:
        if self._dirty:
            self._rebuild_idf()
        if not self._documents:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = {}
        for token in set(query_tokens):
            if token not in self._idf:
                continue
            idf = self._idf[token]
            for doc_id, doc in self._documents.items():
                tf = doc._tf.get(token, 0.0)
                if tf == 0.0:
                    continue
                doc_len = len(doc._tokens)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / max(self._avg_doc_len, 1))
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * (numerator / denominator)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [
            BM25SearchResult(id=doc_id, score=score, metadata=self._documents[doc_id].metadata)
            for doc_id, score in ranked
            if doc_id in self._documents
        ]

    def __len__(self) -> int:
        return len(self._documents)


_kb_indexes: dict[str, BM25Index] = {}


def get_bm25_index(knowledge_base_id: str, k1: float = 1.5, b: float = 0.75) -> BM25Index:
    if knowledge_base_id not in _kb_indexes:
        _kb_indexes[knowledge_base_id] = BM25Index(k1=k1, b=b)
    return _kb_indexes[knowledge_base_id]


def drop_bm25_index(knowledge_base_id: str) -> None:
    _kb_indexes.pop(knowledge_base_id, None)
    
# preprocessing/metadata_extractor.py
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from chunking.base_chunker import count_tokens, split_sentences
from preprocessing.language_detector import detect_language
from preprocessing.pii_detector import pii_type_counts

_WORD_PATTERN = re.compile(r"\b\w+\b")
_URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")
_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+)$", re.MULTILINE)
_CODE_FENCE_PATTERN = re.compile(r"```")
_CODE_INDICATORS: tuple[str, ...] = ("def ", "class ", "function ", "import ", "const ", "let ", "#include", "=>", "{", "}", ";")
_AVERAGE_READING_WPM = 200

_STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our",
        "out", "day", "get", "has", "him", "his", "how", "man", "new", "now", "old", "see", "two",
        "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use", "with", "this",
        "that", "from", "have", "they", "will", "what", "your", "their", "would", "there", "about",
    }
)


def _estimate_title(text: str) -> str | None:
    heading_match = _HEADING_PATTERN.search(text)
    if heading_match:
        return heading_match.group(1).strip()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return None


def _looks_like_code(text: str) -> bool:
    if _CODE_FENCE_PATTERN.search(text):
        return True
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    hits = sum(1 for line in lines if any(indicator in line for indicator in _CODE_INDICATORS))
    return (hits / len(lines)) > 0.15


def extract_metadata(text: str) -> dict[str, Any]:
    extracted_at = datetime.now(timezone.utc).isoformat()

    if not text.strip():
        return {
            "char_count": 0,
            "word_count": 0,
            "sentence_count": 0,
            "token_count": 0,
            "language": "und",
            "language_confidence": 0.0,
            "title": None,
            "has_code": False,
            "url_count": 0,
            "pii_types": {},
            "reading_time_seconds": 0.0,
            "content_hash": hashlib.sha256(b"").hexdigest(),
            "extracted_at": extracted_at,
        }

    words = _WORD_PATTERN.findall(text)
    sentences = split_sentences(text)
    language_result = detect_language(text)

    return {
        "char_count": len(text),
        "word_count": len(words),
        "sentence_count": len(sentences),
        "token_count": count_tokens(text),
        "language": language_result.language,
        "language_confidence": round(language_result.confidence, 4),
        "title": _estimate_title(text),
        "has_code": _looks_like_code(text),
        "url_count": len(_URL_PATTERN.findall(text)),
        "pii_types": pii_type_counts(text),
        "reading_time_seconds": round((len(words) / _AVERAGE_READING_WPM) * 60, 1) if words else 0.0,
        "content_hash": hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest(),
        "extracted_at": extracted_at,
    }


def extract_keywords(text: str, top_k: int = 10, min_word_length: int = 4) -> list[str]:
    words = [word.lower() for word in _WORD_PATTERN.findall(text) if len(word) >= min_word_length]
    frequencies: dict[str, int] = {}
    for word in words:
        if word in _STOPWORDS:
            continue
        frequencies[word] = frequencies.get(word, 0) + 1

    ranked = sorted(frequencies.items(), key=lambda item: item[1], reverse=True)
    return [word for word, _ in ranked[:top_k]]

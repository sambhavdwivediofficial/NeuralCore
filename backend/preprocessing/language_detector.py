# preprocessing/language_detector.py
from __future__ import annotations

from pydantic import BaseModel

try:
    from langdetect import DetectorFactory, LangDetectException, detect_langs

    DetectorFactory.seed = 0
except ImportError:
    DetectorFactory = None
    LangDetectException = Exception
    detect_langs = None

_MIN_TEXT_LENGTH = 10
_RELIABILITY_THRESHOLD = 0.7
_UNKNOWN_LANGUAGE = "und"


class LanguageCandidate(BaseModel):
    language: str
    probability: float


class LanguageDetectionResult(BaseModel):
    language: str
    confidence: float
    is_reliable: bool
    candidates: list[LanguageCandidate] = []


def detect_language(text: str, top_k: int = 3) -> LanguageDetectionResult:
    cleaned = text.strip()
    if len(cleaned) < _MIN_TEXT_LENGTH or detect_langs is None:
        return LanguageDetectionResult(language=_UNKNOWN_LANGUAGE, confidence=0.0, is_reliable=False, candidates=[])

    try:
        results = detect_langs(cleaned)
    except LangDetectException:
        return LanguageDetectionResult(language=_UNKNOWN_LANGUAGE, confidence=0.0, is_reliable=False, candidates=[])

    candidates = [LanguageCandidate(language=item.lang, probability=item.prob) for item in results[:top_k]]
    if not candidates:
        return LanguageDetectionResult(language=_UNKNOWN_LANGUAGE, confidence=0.0, is_reliable=False, candidates=[])

    top = candidates[0]
    return LanguageDetectionResult(
        language=top.language,
        confidence=top.probability,
        is_reliable=top.probability >= _RELIABILITY_THRESHOLD,
        candidates=candidates,
    )


def is_supported_language(language: str, supported: set[str]) -> bool:
    return language in supported

# preprocessing/normalizer.py
from __future__ import annotations

import re
import unicodedata

_WHITESPACE_PATTERN = re.compile(r"[ \t\f\v]+")
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")
_ZERO_WIDTH_PATTERN = re.compile(r"[\u200b\u200c\u200d\ufeff\u2060]")
_SMART_QUOTES: dict[str, str] = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
}


def normalize_unicode(text: str, form: str = "NFKC") -> str:
    return unicodedata.normalize(form, text)


def remove_zero_width_characters(text: str) -> str:
    return _ZERO_WIDTH_PATTERN.sub("", text)


def normalize_smart_quotes(text: str) -> str:
    for source, target in _SMART_QUOTES.items():
        text = text.replace(source, target)
    return text


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_PATTERN.sub(" ", text)
    text = _MULTI_NEWLINE_PATTERN.sub("\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_text(
    text: str,
    lowercase: bool = False,
    strip_accent_marks: bool = False,
    unicode_form: str = "NFKC",
) -> str:
    text = normalize_unicode(text, unicode_form)
    text = remove_zero_width_characters(text)
    text = normalize_smart_quotes(text)
    text = normalize_whitespace(text)
    if strip_accent_marks:
        text = strip_accents(text)
    if lowercase:
        text = text.lower()
    return text

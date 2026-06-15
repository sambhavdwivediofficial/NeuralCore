# preprocessing/cleaner.py
from __future__ import annotations

import html
import re
from dataclasses import dataclass

from preprocessing.normalizer import normalize_text

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")
_REPEATED_PUNCTUATION_PATTERN = re.compile(r"([!?.,;:]){3,}")
_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\((?:[^)]*)\)")


@dataclass(slots=True)
class CleaningOptions:
    strip_html: bool = True
    decode_entities: bool = True
    remove_control_characters: bool = True
    collapse_repeated_punctuation: bool = True
    normalize_markdown_links: bool = False
    remove_urls: bool = False
    normalize: bool = True
    lowercase: bool = False


_DEFAULT_OPTIONS = CleaningOptions()


def strip_html_tags(text: str) -> str:
    return _HTML_TAG_PATTERN.sub(" ", text)


def decode_html_entities(text: str) -> str:
    return html.unescape(text)


def remove_control_characters(text: str) -> str:
    return _CONTROL_CHAR_PATTERN.sub("", text)


def collapse_repeated_punctuation(text: str) -> str:
    return _REPEATED_PUNCTUATION_PATTERN.sub(lambda match: match.group(1) * 3, text)


def normalize_markdown_links(text: str) -> str:
    return _MARKDOWN_LINK_PATTERN.sub(r"\1", text)


def remove_urls(text: str) -> str:
    return _URL_PATTERN.sub("", text)


def clean_text(text: str, options: CleaningOptions | None = None) -> str:
    if not text:
        return ""

    options = options or _DEFAULT_OPTIONS
    cleaned = text

    if options.decode_entities:
        cleaned = decode_html_entities(cleaned)
    if options.strip_html:
        cleaned = strip_html_tags(cleaned)
    if options.remove_control_characters:
        cleaned = remove_control_characters(cleaned)
    if options.normalize_markdown_links:
        cleaned = normalize_markdown_links(cleaned)
    if options.remove_urls:
        cleaned = remove_urls(cleaned)
    if options.collapse_repeated_punctuation:
        cleaned = collapse_repeated_punctuation(cleaned)
    if options.normalize:
        cleaned = normalize_text(cleaned, lowercase=options.lowercase)

    return cleaned

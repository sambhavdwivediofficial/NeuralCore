# finetuning/dataset_cleaner.py
from __future__ import annotations

from typing import Any

from preprocessing.deduplicator import compute_content_hash
from preprocessing.normalizer import normalize_text
from preprocessing.pii_detector import contains_pii, redact_pii


def clean_dataset_records(
    records: list[dict[str, Any]],
    text_fields: list[str],
    remove_duplicates: bool = True,
    redact_sensitive: bool = True,
    normalize_whitespace: bool = True,
    min_field_length: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {"original_count": len(records), "removed_duplicates": 0, "removed_too_short": 0, "redacted_pii": 0, "final_count": 0}

    seen_hashes: set[str] = set()
    cleaned_records: list[dict[str, Any]] = []

    for record in records:
        record = dict(record)
        too_short = False
        had_pii = False

        for field_name in text_fields:
            if field_name not in record:
                continue
            value = str(record[field_name])

            if normalize_whitespace:
                value = normalize_text(value)

            if redact_sensitive and contains_pii(value):
                value = redact_pii(value)
                had_pii = True

            if len(value.strip()) < min_field_length:
                too_short = True

            record[field_name] = value

        if too_short:
            stats["removed_too_short"] += 1
            continue

        if had_pii:
            stats["redacted_pii"] += 1

        if remove_duplicates:
            record_hash = compute_content_hash(str({k: record.get(k) for k in text_fields}))
            if record_hash in seen_hashes:
                stats["removed_duplicates"] += 1
                continue
            seen_hashes.add(record_hash)

        cleaned_records.append(record)

    stats["final_count"] = len(cleaned_records)
    return cleaned_records, stats


def filter_by_length(
    records: list[dict[str, Any]],
    text_field: str,
    min_length: int = 10,
    max_length: int = 32000,
) -> list[dict[str, Any]]:
    return [r for r in records if min_length <= len(str(r.get(text_field, ""))) <= max_length]


def balance_dataset_by_category(
    records: list[dict[str, Any]],
    category_field: str,
    max_per_category: int | None = None,
) -> list[dict[str, Any]]:
    from collections import defaultdict

    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record.get(category_field)].append(record)

    if max_per_category is None:
        max_per_category = min(len(items) for items in grouped.values()) if grouped else 0

    balanced: list[dict[str, Any]] = []
    for items in grouped.values():
        balanced.extend(items[:max_per_category])
    return balanced

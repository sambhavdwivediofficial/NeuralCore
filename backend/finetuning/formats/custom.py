# finetuning/formats/custom.py
from __future__ import annotations

import csv
import json
from typing import Any, Callable


class CustomFormatError(ValueError):
    pass


def load_custom_format(
    file_path: str,
    field_mapping: dict[str, str],
    file_format: str = "jsonl",
) -> list[dict[str, Any]]:
    raw_records: list[dict[str, Any]] = []

    if file_format == "jsonl":
        with open(file_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    raw_records.append(json.loads(line))
    elif file_format == "json":
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            raw_records = data if isinstance(data, list) else [data]
    elif file_format == "csv":
        with open(file_path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            raw_records = list(reader)
    else:
        raise CustomFormatError(f"Unsupported file format: {file_format}")

    normalized: list[dict[str, Any]] = []
    for raw in raw_records:
        record: dict[str, Any] = {}
        for target_field, source_field in field_mapping.items():
            record[target_field] = raw.get(source_field, "")
        normalized.append(record)

    return normalized


def custom_to_chat_messages(
    record: dict[str, Any],
    converter: Callable[[dict[str, Any]], list[dict[str, str]]] | None = None,
) -> list[dict[str, str]]:
    if converter is not None:
        return converter(record)

    messages: list[dict[str, str]] = []
    if "system" in record and record["system"]:
        messages.append({"role": "system", "content": record["system"]})
    if "input" in record and record["input"]:
        messages.append({"role": "user", "content": record["input"]})
    if "output" in record and record["output"]:
        messages.append({"role": "assistant", "content": record["output"]})
    return messages

# finetuning/formats/openai.py
from __future__ import annotations

import json
from typing import Any


def validate_openai_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    messages = record.get("messages", [])
    if not messages or not isinstance(messages, list):
        errors.append("missing or empty 'messages' array")
        return errors

    valid_roles = {"system", "user", "assistant", "tool"}
    has_assistant = False
    for index, message in enumerate(messages):
        role = message.get("role")
        if role not in valid_roles:
            errors.append(f"message {index} has invalid role '{role}'")
        if role == "assistant":
            has_assistant = True
        if "content" not in message and "tool_calls" not in message:
            errors.append(f"message {index} missing 'content' or 'tool_calls'")

    if not has_assistant:
        errors.append("conversation must contain at least one assistant message")

    return errors


def openai_to_chat_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    return [{"role": m["role"], "content": m.get("content", "")} for m in record.get("messages", [])]


def chat_messages_to_openai(messages: list[dict[str, str]]) -> dict[str, Any]:
    return {"messages": [{"role": m["role"], "content": m["content"]} for m in messages]}


def load_openai_jsonl_dataset(file_path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return records


def save_openai_jsonl_dataset(records: list[dict[str, Any]], file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

# finetuning/formats/sharegpt.py
from __future__ import annotations

import json
from typing import Any

_ROLE_MAP_TO_SHAREGPT: dict[str, str] = {"system": "system", "user": "human", "assistant": "gpt", "tool": "tool"}
_ROLE_MAP_FROM_SHAREGPT: dict[str, str] = {v: k for k, v in _ROLE_MAP_TO_SHAREGPT.items()}


def validate_sharegpt_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    conversations = record.get("conversations", [])
    if not conversations or not isinstance(conversations, list):
        errors.append("missing or empty 'conversations' array")
        return errors
    for index, turn in enumerate(conversations):
        if "from" not in turn:
            errors.append(f"conversation turn {index} missing 'from' field")
        if "value" not in turn or not str(turn.get("value", "")).strip():
            errors.append(f"conversation turn {index} missing or empty 'value' field")
    return errors


def sharegpt_to_chat_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for turn in record.get("conversations", []):
        sender = turn.get("from", "human")
        role = _ROLE_MAP_FROM_SHAREGPT.get(sender, "user")
        messages.append({"role": role, "content": turn.get("value", "")})
    return messages


def chat_messages_to_sharegpt(messages: list[dict[str, str]], system_prompt: str | None = None) -> dict[str, Any]:
    conversations: list[dict[str, str]] = []
    if system_prompt:
        conversations.append({"from": "system", "value": system_prompt})
    for message in messages:
        sender = _ROLE_MAP_TO_SHAREGPT.get(message["role"], "human")
        conversations.append({"from": sender, "value": message["content"]})
    return {"conversations": conversations}


def load_sharegpt_dataset(file_path: str) -> list[dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("ShareGPT dataset file must contain a JSON array")
    return data


def save_sharegpt_dataset(records: list[dict[str, Any]], file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)

# finetuning/formats/alpaca.py
from __future__ import annotations

import json
from typing import Any

_ALPACA_PROMPT_TEMPLATE_WITH_INPUT = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Input:
{input}

### Response:
{output}"""

_ALPACA_PROMPT_TEMPLATE_NO_INPUT = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Response:
{output}"""


def validate_alpaca_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "instruction" not in record or not str(record.get("instruction", "")).strip():
        errors.append("missing or empty 'instruction' field")
    if "output" not in record or not str(record.get("output", "")).strip():
        errors.append("missing or empty 'output' field")
    return errors


def alpaca_to_text(record: dict[str, Any]) -> str:
    instruction = record.get("instruction", "")
    input_text = record.get("input", "")
    output = record.get("output", "")
    if input_text and input_text.strip():
        return _ALPACA_PROMPT_TEMPLATE_WITH_INPUT.format(instruction=instruction, input=input_text, output=output)
    return _ALPACA_PROMPT_TEMPLATE_NO_INPUT.format(instruction=instruction, output=output)


def alpaca_to_chat_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    instruction = record.get("instruction", "")
    input_text = record.get("input", "")
    output = record.get("output", "")
    user_content = f"{instruction}\n\n{input_text}".strip() if input_text else instruction
    return [
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": output},
    ]


def load_alpaca_dataset(file_path: str) -> list[dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Alpaca dataset file must contain a JSON array")
    return data


def save_alpaca_dataset(records: list[dict[str, Any]], file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)

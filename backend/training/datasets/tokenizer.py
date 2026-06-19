# training/datasets/tokenizer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chunking.base_chunker import count_tokens


@dataclass(slots=True)
class TokenizedBatch:
    input_ids: list[list[int]]
    attention_mask: list[list[int]]
    labels: list[list[int]] | None = None


class TrainingTokenizer:
    def __init__(self, model_path: str, max_length: int = 2048) -> None:
        self.model_path = model_path
        self.max_length = max_length
        self._tokenizer: Any = None

    def _load(self) -> Any:
        if self._tokenizer is None:
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
        return self._tokenizer

    def tokenize_text(self, text: str, truncation: bool = True) -> dict[str, list[int]]:
        tokenizer = self._load()
        encoded = tokenizer(text, truncation=truncation, max_length=self.max_length, padding="max_length")
        return {"input_ids": encoded["input_ids"], "attention_mask": encoded["attention_mask"]}

    def tokenize_batch(self, texts: list[str]) -> TokenizedBatch:
        tokenizer = self._load()
        encoded = tokenizer(texts, truncation=True, max_length=self.max_length, padding="max_length")
        return TokenizedBatch(input_ids=encoded["input_ids"], attention_mask=encoded["attention_mask"])

    def tokenize_chat_messages(self, messages: list[dict[str, str]]) -> dict[str, list[int]]:
        tokenizer = self._load()
        if hasattr(tokenizer, "apply_chat_template"):
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        else:
            text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        return self.tokenize_text(text)

    def mask_prompt_labels(self, input_ids: list[int], prompt_length: int, pad_token_id: int) -> list[int]:
        labels = list(input_ids)
        for i in range(min(prompt_length, len(labels))):
            labels[i] = -100
        for i, token_id in enumerate(labels):
            if input_ids[i] == pad_token_id:
                labels[i] = -100
        return labels

    def estimate_token_count(self, text: str) -> int:
        return count_tokens(text)

    def vocab_size(self) -> int:
        tokenizer = self._load()
        return tokenizer.vocab_size

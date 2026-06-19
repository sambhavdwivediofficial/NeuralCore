# finetuning/dataset_builder.py
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from finetuning.dataset_cleaner import clean_dataset_records
from finetuning.dataset_validator import DatasetFormatType, DatasetValidationReport, validate_dataset
from monitoring.logging import get_logger

logger = get_logger("neuralcore.finetuning.dataset_builder")


@dataclass(slots=True)
class DatasetSplit:
    train: list[dict[str, Any]]
    validation: list[dict[str, Any]]
    test: list[dict[str, Any]]

    def to_dict(self) -> dict[str, int]:
        return {"train": len(self.train), "validation": len(self.validation), "test": len(self.test)}


class DatasetBuilder:
    def __init__(self, format_type: DatasetFormatType) -> None:
        self.format_type = format_type
        self._records: list[dict[str, Any]] = []

    def add_record(self, record: dict[str, Any]) -> "DatasetBuilder":
        self._records.append(record)
        return self

    def add_records(self, records: list[dict[str, Any]]) -> "DatasetBuilder":
        self._records.extend(records)
        return self

    def from_conversations(self, conversations: list[list[dict[str, str]]]) -> "DatasetBuilder":
        if self.format_type == DatasetFormatType.SHAREGPT:
            from finetuning.formats.sharegpt import chat_messages_to_sharegpt
            for messages in conversations:
                self._records.append(chat_messages_to_sharegpt(messages))
        elif self.format_type == DatasetFormatType.OPENAI:
            from finetuning.formats.openai import chat_messages_to_openai
            for messages in conversations:
                self._records.append(chat_messages_to_openai(messages))
        return self

    def clean(self, text_fields: list[str], **kwargs: Any) -> "DatasetBuilder":
        self._records, stats = clean_dataset_records(self._records, text_fields, **kwargs)
        logger.info("dataset_cleaned", **stats)
        return self

    def validate(self, max_tokens_per_record: int = 8192) -> DatasetValidationReport:
        return validate_dataset(self._records, self.format_type, max_tokens_per_record)

    def deduplicate(self, text_fields: list[str]) -> "DatasetBuilder":
        self._records, _ = clean_dataset_records(self._records, text_fields, remove_duplicates=True, redact_sensitive=False, normalize_whitespace=False)
        return self

    def shuffle(self, seed: int | None = None) -> "DatasetBuilder":
        rng = random.Random(seed)
        rng.shuffle(self._records)
        return self

    def split(
        self,
        train_ratio: float = 0.8,
        validation_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> DatasetSplit:
        if abs((train_ratio + validation_ratio + test_ratio) - 1.0) > 1e-6:
            raise ValueError("Split ratios must sum to 1.0")

        records = list(self._records)
        random.Random(seed).shuffle(records)

        n = len(records)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * validation_ratio)

        return DatasetSplit(
            train=records[:train_end],
            validation=records[train_end:val_end],
            test=records[val_end:],
        )

    def build(self) -> list[dict[str, Any]]:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)

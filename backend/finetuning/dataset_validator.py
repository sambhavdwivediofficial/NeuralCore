# finetuning/dataset_validator.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from chunking.base_chunker import count_tokens


class DatasetFormatType(str, Enum):
    ALPACA = "alpaca"
    SHAREGPT = "sharegpt"
    OPENAI = "openai"
    CUSTOM = "custom"


@dataclass(slots=True)
class ValidationIssue:
    record_index: int
    severity: str
    message: str


@dataclass(slots=True)
class DatasetValidationReport:
    total_records: int
    valid_records: int
    invalid_records: int
    issues: list[ValidationIssue] = field(default_factory=list)
    avg_token_count: float = 0.0
    max_token_count: int = 0
    min_token_count: int = 0
    duplicate_count: int = 0

    @property
    def is_valid(self) -> bool:
        return self.invalid_records == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "is_valid": self.is_valid,
            "issues": [{"record_index": i.record_index, "severity": i.severity, "message": i.message} for i in self.issues[:200]],
            "issue_count": len(self.issues),
            "avg_token_count": round(self.avg_token_count, 1),
            "max_token_count": self.max_token_count,
            "min_token_count": self.min_token_count,
            "duplicate_count": self.duplicate_count,
        }


def validate_dataset(
    records: list[dict[str, Any]],
    format_type: DatasetFormatType,
    max_tokens_per_record: int = 8192,
) -> DatasetValidationReport:
    from finetuning.formats.alpaca import validate_alpaca_record
    from finetuning.formats.openai import validate_openai_record
    from finetuning.formats.sharegpt import validate_sharegpt_record

    validator_map = {
        DatasetFormatType.ALPACA: validate_alpaca_record,
        DatasetFormatType.SHAREGPT: validate_sharegpt_record,
        DatasetFormatType.OPENAI: validate_openai_record,
    }
    validator = validator_map.get(format_type)

    issues: list[ValidationIssue] = []
    token_counts: list[int] = []
    seen_hashes: set[str] = set()
    duplicate_count = 0
    valid_count = 0

    for index, record in enumerate(records):
        record_errors: list[str] = validator(record) if validator else []

        record_text = str(record)
        token_count = count_tokens(record_text)
        token_counts.append(token_count)

        if token_count > max_tokens_per_record:
            record_errors.append(f"record exceeds max token limit ({token_count} > {max_tokens_per_record})")

        import hashlib
        record_hash = hashlib.sha256(record_text.encode("utf-8", errors="ignore")).hexdigest()
        if record_hash in seen_hashes:
            duplicate_count += 1
            issues.append(ValidationIssue(record_index=index, severity="warning", message="duplicate record detected"))
        else:
            seen_hashes.add(record_hash)

        if record_errors:
            for error in record_errors:
                issues.append(ValidationIssue(record_index=index, severity="error", message=error))
        else:
            valid_count += 1

    return DatasetValidationReport(
        total_records=len(records),
        valid_records=valid_count,
        invalid_records=len(records) - valid_count,
        issues=issues,
        avg_token_count=sum(token_counts) / len(token_counts) if token_counts else 0.0,
        max_token_count=max(token_counts, default=0),
        min_token_count=min(token_counts, default=0),
        duplicate_count=duplicate_count,
    )

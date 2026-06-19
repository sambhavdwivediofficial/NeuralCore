# training/datasets/preprocessor.py
from __future__ import annotations

from typing import Any, Callable

from chunking.base_chunker import count_tokens
from preprocessing.cleaner import CleaningOptions, clean_text
from preprocessing.deduplicator import compute_simhash, hamming_distance


class StreamingPreprocessor:
    def __init__(
        self,
        text_field: str = "text",
        min_tokens: int = 8,
        max_tokens: int = 8192,
        dedup_threshold: int = 3,
        clean_options: CleaningOptions | None = None,
    ) -> None:
        self.text_field = text_field
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.dedup_threshold = dedup_threshold
        self.clean_options = clean_options or CleaningOptions(strip_html=True, normalize=True)
        self._seen_fingerprints: list[int] = []
        self._fingerprint_cap = 100_000

    def process(self, record: dict[str, Any]) -> dict[str, Any] | None:
        text = record.get(self.text_field, "")
        if not text or not isinstance(text, str):
            return None

        cleaned = clean_text(text, self.clean_options)
        token_count = count_tokens(cleaned)

        if token_count < self.min_tokens or token_count > self.max_tokens:
            return None

        fingerprint = compute_simhash(cleaned)
        if self._is_near_duplicate(fingerprint):
            return None

        self._register_fingerprint(fingerprint)

        return {**record, self.text_field: cleaned, "_token_count": token_count}

    def _is_near_duplicate(self, fingerprint: int) -> bool:
        if self.dedup_threshold < 0:
            return False
        return any(hamming_distance(fingerprint, existing) <= self.dedup_threshold for existing in self._seen_fingerprints[-5000:])

    def _register_fingerprint(self, fingerprint: int) -> None:
        self._seen_fingerprints.append(fingerprint)
        if len(self._seen_fingerprints) > self._fingerprint_cap:
            self._seen_fingerprints = self._seen_fingerprints[-self._fingerprint_cap // 2 :]

    def process_stream(self, records: Any) -> Any:
        for record in records:
            processed = self.process(record)
            if processed is not None:
                yield processed

    def reset(self) -> None:
        self._seen_fingerprints.clear()


def build_packing_function(max_seq_length: int, eos_token_id: int) -> Callable[[list[list[int]]], list[list[int]]]:
    def _pack(token_sequences: list[list[int]]) -> list[list[int]]:
        packed: list[list[int]] = []
        buffer: list[int] = []

        for sequence in token_sequences:
            buffer.extend(sequence + [eos_token_id])
            while len(buffer) >= max_seq_length:
                packed.append(buffer[:max_seq_length])
                buffer = buffer[max_seq_length:]

        if buffer:
            padding_needed = max_seq_length - len(buffer)
            packed.append(buffer + [eos_token_id] * padding_needed)

        return packed

    return _pack

# training/datasets/loader.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.dataset_loader")


@dataclass(slots=True)
class DatasetSource:
    path: str
    format: str = "jsonl"
    text_field: str = "text"
    weight: float = 1.0


class StreamingDatasetLoader:
    def __init__(self, sources: list[DatasetSource], shuffle_buffer_size: int = 10000, seed: int = 42) -> None:
        self.sources = sources
        self.shuffle_buffer_size = shuffle_buffer_size
        self.seed = seed

    def load_hf_dataset(self, streaming: bool = True) -> Any:
        try:
            from datasets import interleave_datasets, load_dataset
        except ImportError as exc:
            raise ImportError("datasets library not installed; run: pip install -r requirements-worker.txt") from exc

        loaded: list[Any] = []
        weights: list[float] = []

        for source in self.sources:
            data_files = source.path
            ds = load_dataset(source.format, data_files=data_files, streaming=streaming, split="train")
            loaded.append(ds)
            weights.append(source.weight)

        if len(loaded) == 1:
            combined = loaded[0]
        else:
            total = sum(weights)
            probs = [w / total for w in weights]
            combined = interleave_datasets(loaded, probabilities=probs, seed=self.seed)

        if streaming and self.shuffle_buffer_size > 0:
            combined = combined.shuffle(seed=self.seed, buffer_size=self.shuffle_buffer_size)

        return combined

    def count_total_examples(self) -> int:
        total = 0
        for source in self.sources:
            path = Path(source.path)
            if not path.exists():
                continue
            if source.format == "jsonl":
                with open(path, "r", encoding="utf-8") as handle:
                    total += sum(1 for line in handle if line.strip())
            elif source.format == "json":
                import json
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    total += len(data) if isinstance(data, list) else 1
        return total

    def iter_raw_records(self) -> Iterator[dict[str, Any]]:
        import json
        for source in self.sources:
            path = Path(source.path)
            if source.format == "jsonl":
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if line:
                            yield json.loads(line)
            elif source.format == "json":
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    items = data if isinstance(data, list) else [data]
                    yield from items

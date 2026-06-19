# training/datasets/sampler.py
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(slots=True)
class DataSourceWeight:
    source_name: str
    weight: float
    examples: list[dict[str, Any]]


class WeightedMultiSourceSampler:
    def __init__(self, sources: list[DataSourceWeight], seed: int = 42) -> None:
        self.sources = sources
        self._rng = random.Random(seed)
        total = sum(s.weight for s in sources)
        self._probabilities = [s.weight / total for s in sources] if total > 0 else []

    def sample_one(self) -> dict[str, Any] | None:
        if not self.sources:
            return None
        source = self._rng.choices(self.sources, weights=self._probabilities, k=1)[0]
        if not source.examples:
            return None
        return self._rng.choice(source.examples)

    def sample_batch(self, batch_size: int) -> list[dict[str, Any]]:
        batch: list[dict[str, Any]] = []
        for _ in range(batch_size):
            sample = self.sample_one()
            if sample is not None:
                batch.append(sample)
        return batch

    def iter_epoch(self) -> Iterator[dict[str, Any]]:
        total_examples = sum(len(s.examples) for s in self.sources)
        for _ in range(total_examples):
            sample = self.sample_one()
            if sample is not None:
                yield sample

    def curriculum_sample(self, difficulty_fn: Any, current_step: int, total_steps: int) -> dict[str, Any] | None:
        progress = min(current_step / max(total_steps, 1), 1.0)
        max_difficulty = progress

        eligible_sources = [
            s for s in self.sources
            if not s.examples or difficulty_fn(s.examples[0]) <= max_difficulty
        ]
        if not eligible_sources:
            eligible_sources = self.sources

        total = sum(s.weight for s in eligible_sources)
        if total == 0:
            return None
        probs = [s.weight / total for s in eligible_sources]
        source = self._rng.choices(eligible_sources, weights=probs, k=1)[0]
        return self._rng.choice(source.examples) if source.examples else None

    def rebalance_weights(self, loss_per_source: dict[str, float], temperature: float = 1.0) -> None:
        import math
        for source in self.sources:
            loss = loss_per_source.get(source.source_name, 1.0)
            source.weight = math.exp(loss / temperature)
        total = sum(s.weight for s in self.sources)
        self._probabilities = [s.weight / total for s in self.sources] if total > 0 else []

# training/optimization/scheduler.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SchedulerConfig:
    name: str = "cosine"
    num_warmup_steps: int = 0
    num_training_steps: int = 1000
    min_lr_ratio: float = 0.1
    num_cycles: float = 0.5


def build_lr_scheduler(optimizer: Any, config: SchedulerConfig) -> Any:
    try:
        from transformers import get_scheduler
    except ImportError as exc:
        raise ImportError("transformers not installed; run: pip install -r requirements-worker.txt") from exc

    return get_scheduler(
        name=config.name,
        optimizer=optimizer,
        num_warmup_steps=config.num_warmup_steps,
        num_training_steps=config.num_training_steps,
    )


def cosine_with_min_lr(step: int, config: SchedulerConfig, base_lr: float) -> float:
    if step < config.num_warmup_steps:
        return base_lr * (step / max(config.num_warmup_steps, 1))

    progress = (step - config.num_warmup_steps) / max(config.num_training_steps - config.num_warmup_steps, 1)
    progress = min(progress, 1.0)
    cosine_decay = 0.5 * (1 + math.cos(math.pi * config.num_cycles * 2 * progress))
    min_lr = base_lr * config.min_lr_ratio
    return min_lr + (base_lr - min_lr) * cosine_decay


def linear_warmup_steps_from_ratio(total_steps: int, warmup_ratio: float) -> int:
    return max(1, int(total_steps * warmup_ratio))

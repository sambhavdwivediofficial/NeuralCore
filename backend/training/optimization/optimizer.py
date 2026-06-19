# training/optimization/optimizer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OptimizerConfig:
    name: str = "adamw_torch"
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    beta1: float = 0.9
    beta2: float = 0.999
    epsilon: float = 1e-8
    max_grad_norm: float = 1.0
    use_8bit: bool = False


def build_optimizer(model: Any, config: OptimizerConfig) -> Any:
    try:
        import torch
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    trainable_params = [p for p in model.parameters() if p.requires_grad]

    if config.use_8bit:
        try:
            import bitsandbytes as bnb
            return bnb.optim.AdamW8bit(
                trainable_params, lr=config.learning_rate, betas=(config.beta1, config.beta2),
                eps=config.epsilon, weight_decay=config.weight_decay,
            )
        except ImportError:
            pass

    if config.name == "adamw_torch":
        return torch.optim.AdamW(
            trainable_params, lr=config.learning_rate, betas=(config.beta1, config.beta2),
            eps=config.epsilon, weight_decay=config.weight_decay,
        )
    if config.name == "sgd":
        return torch.optim.SGD(trainable_params, lr=config.learning_rate, weight_decay=config.weight_decay, momentum=0.9)
    if config.name == "adafactor":
        from transformers.optimization import Adafactor
        return Adafactor(trainable_params, lr=config.learning_rate, scale_parameter=False, relative_step=False)

    raise ValueError(f"Unknown optimizer: {config.name}")


def count_trainable_parameters(model: Any) -> dict[str, int]:
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return {"trainable_params": trainable, "total_params": total, "trainable_percentage": round(100 * trainable / max(total, 1), 4)}

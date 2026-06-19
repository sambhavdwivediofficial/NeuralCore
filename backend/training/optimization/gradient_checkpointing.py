# training/optimization/gradient_checkpointing.py
from __future__ import annotations

from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.gradient_checkpointing")


def enable_gradient_checkpointing(model: Any, use_reentrant: bool = False) -> None:
    if hasattr(model, "gradient_checkpointing_enable"):
        try:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": use_reentrant})
        except TypeError:
            model.gradient_checkpointing_enable()
        logger.info("gradient_checkpointing_enabled", use_reentrant=use_reentrant)
    else:
        logger.warning("model_does_not_support_gradient_checkpointing")


def disable_gradient_checkpointing(model: Any) -> None:
    if hasattr(model, "gradient_checkpointing_disable"):
        model.gradient_checkpointing_disable()


def estimate_memory_savings(num_layers: int, hidden_size: int, seq_length: int, batch_size: int) -> dict[str, float]:
    bytes_per_activation = 2
    activation_memory_without_gb = (num_layers * hidden_size * seq_length * batch_size * bytes_per_activation) / (1024 ** 3)
    activation_memory_with_gb = activation_memory_without_gb / max(num_layers ** 0.5, 1)

    return {
        "without_checkpointing_gb": round(activation_memory_without_gb, 2),
        "with_checkpointing_gb": round(activation_memory_with_gb, 2),
        "savings_gb": round(activation_memory_without_gb - activation_memory_with_gb, 2),
        "savings_percentage": round(100 * (1 - activation_memory_with_gb / max(activation_memory_without_gb, 1e-9)), 1),
    }

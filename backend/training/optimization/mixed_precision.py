# training/optimization/mixed_precision.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MixedPrecisionConfig:
    enabled: bool = True
    dtype: str = "bfloat16"
    loss_scale: str = "dynamic"


def get_autocast_dtype(config: MixedPrecisionConfig) -> Any:
    try:
        import torch
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    mapping = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
    return mapping.get(config.dtype, torch.bfloat16)


def supports_bfloat16() -> bool:
    try:
        import torch
        return torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    except ImportError:
        return False


def recommend_precision_config() -> MixedPrecisionConfig:
    if supports_bfloat16():
        return MixedPrecisionConfig(enabled=True, dtype="bfloat16")

    try:
        import torch
        if torch.cuda.is_available():
            return MixedPrecisionConfig(enabled=True, dtype="float16", loss_scale="dynamic")
    except ImportError:
        pass

    return MixedPrecisionConfig(enabled=False, dtype="float32")


class GradScalerWrapper:
    def __init__(self, config: MixedPrecisionConfig) -> None:
        self.config = config
        self._scaler: Any = None
        if config.enabled and config.dtype == "float16":
            try:
                import torch
                self._scaler = torch.cuda.amp.GradScaler()
            except ImportError:
                pass

    def scale_loss(self, loss: Any) -> Any:
        return self._scaler.scale(loss) if self._scaler else loss

    def step(self, optimizer: Any) -> None:
        if self._scaler:
            self._scaler.step(optimizer)
            self._scaler.update()
        else:
            optimizer.step()

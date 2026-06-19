# finetuning/lora/lora.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LoRAConfig:
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"
    modules_to_save: list[str] | None = None
    fan_in_fan_out: bool = False

    @property
    def scaling_factor(self) -> float:
        return self.lora_alpha / self.r

    def estimate_trainable_params(self, hidden_size: int, num_layers: int) -> int:
        params_per_module = self.r * hidden_size * 2
        return params_per_module * len(self.target_modules) * num_layers

    def to_peft_config_dict(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "r": self.r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "target_modules": self.target_modules,
            "bias": self.bias,
            "task_type": self.task_type,
            "fan_in_fan_out": self.fan_in_fan_out,
        }
        if self.modules_to_save:
            config["modules_to_save"] = self.modules_to_save
        return config


def build_peft_lora_config(config: LoRAConfig) -> Any:
    try:
        from peft import LoraConfig, TaskType
    except ImportError as exc:
        raise ImportError("peft is not installed; run: pip install peft (in requirements-worker.txt)") from exc

    task_type = getattr(TaskType, config.task_type, TaskType.CAUSAL_LM)
    return LoraConfig(
        r=config.r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.target_modules,
        bias=config.bias,
        task_type=task_type,
        fan_in_fan_out=config.fan_in_fan_out,
        modules_to_save=config.modules_to_save,
    )


def get_recommended_lora_config(model_size_billions: float) -> LoRAConfig:
    if model_size_billions <= 3:
        return LoRAConfig(r=8, lora_alpha=16)
    if model_size_billions <= 13:
        return LoRAConfig(r=16, lora_alpha=32)
    if model_size_billions <= 34:
        return LoRAConfig(r=32, lora_alpha=64)
    return LoRAConfig(r=64, lora_alpha=128)

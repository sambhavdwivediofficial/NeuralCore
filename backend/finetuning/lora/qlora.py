# finetuning/lora/qlora.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finetuning.lora.lora import LoRAConfig


@dataclass(slots=True)
class QLoRAConfig:
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_use_double_quant: bool = True
    lora: LoRAConfig | None = None

    def __post_init__(self) -> None:
        if self.lora is None:
            self.lora = LoRAConfig()

    def estimate_vram_gb(self, model_size_billions: float) -> float:
        bytes_per_param_4bit = 0.5
        base_vram = model_size_billions * bytes_per_param_4bit
        overhead_factor = 1.3
        return round(base_vram * overhead_factor, 2)

    def to_bnb_config_dict(self) -> dict[str, Any]:
        return {
            "load_in_4bit": self.load_in_4bit,
            "bnb_4bit_quant_type": self.bnb_4bit_quant_type,
            "bnb_4bit_compute_dtype": self.bnb_4bit_compute_dtype,
            "bnb_4bit_use_double_quant": self.bnb_4bit_use_double_quant,
        }


def build_bnb_quantization_config(config: QLoRAConfig) -> Any:
    try:
        import torch
        from transformers import BitsAndBytesConfig
    except ImportError as exc:
        raise ImportError("transformers/torch not installed; run: pip install -r requirements-worker.txt") from exc

    compute_dtype = getattr(torch, config.bnb_4bit_compute_dtype, torch.bfloat16)
    return BitsAndBytesConfig(
        load_in_4bit=config.load_in_4bit,
        bnb_4bit_quant_type=config.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=config.bnb_4bit_use_double_quant,
    )


def get_recommended_qlora_config(available_vram_gb: float, model_size_billions: float) -> QLoRAConfig:
    config = QLoRAConfig()
    estimated_need = config.estimate_vram_gb(model_size_billions)

    if available_vram_gb < estimated_need:
        config.lora.r = max(4, config.lora.r // 2)
        config.lora.target_modules = ["q_proj", "v_proj"]

    return config

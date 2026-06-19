# training/distributed/deepspeed.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.distributed.deepspeed")


@dataclass(slots=True)
class DeepSpeedConfig:
    zero_stage: int = 2
    offload_optimizer: bool = False
    offload_parameters: bool = False
    gradient_accumulation_steps: int = 4
    train_micro_batch_size_per_gpu: int = 4
    fp16_enabled: bool = False
    bf16_enabled: bool = True

    def to_ds_config_dict(self) -> dict[str, Any]:
        zero_config: dict[str, Any] = {"stage": self.zero_stage}

        if self.offload_optimizer:
            zero_config["offload_optimizer"] = {"device": "cpu", "pin_memory": True}
        if self.offload_parameters and self.zero_stage == 3:
            zero_config["offload_param"] = {"device": "cpu", "pin_memory": True}

        if self.zero_stage == 3:
            zero_config.update({
                "stage3_prefetch_bucket_size": 5e8,
                "stage3_param_persistence_threshold": 1e6,
                "stage3_max_live_parameters": 1e9,
            })

        return {
            "train_micro_batch_size_per_gpu": self.train_micro_batch_size_per_gpu,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "zero_optimization": zero_config,
            "fp16": {"enabled": self.fp16_enabled},
            "bf16": {"enabled": self.bf16_enabled},
            "gradient_clipping": 1.0,
            "steps_per_print": 50,
            "wall_clock_breakdown": False,
        }


def recommend_deepspeed_config(model_size_billions: float, available_vram_gb: float, num_gpus: int = 1) -> DeepSpeedConfig:
    params_memory_gb = model_size_billions * 4
    optimizer_memory_gb = model_size_billions * 12

    total_needed_per_gpu = (params_memory_gb + optimizer_memory_gb) / num_gpus

    if total_needed_per_gpu <= available_vram_gb * 0.7:
        return DeepSpeedConfig(zero_stage=2, offload_optimizer=False)
    if total_needed_per_gpu / 2 <= available_vram_gb * 0.7:
        return DeepSpeedConfig(zero_stage=2, offload_optimizer=True)

    return DeepSpeedConfig(zero_stage=3, offload_optimizer=True, offload_parameters=True)


def init_deepspeed_engine(model: Any, config: DeepSpeedConfig, model_parameters: Any = None) -> tuple[Any, Any, Any, Any]:
    try:
        import deepspeed
    except ImportError as exc:
        raise ImportError("deepspeed not installed; run: pip install deepspeed (requirements-worker.txt)") from exc

    ds_config = config.to_ds_config_dict()
    engine, optimizer, _, lr_scheduler = deepspeed.initialize(
        model=model, model_parameters=model_parameters or model.parameters(), config=ds_config,
    )
    logger.info("deepspeed_engine_initialized", zero_stage=config.zero_stage)
    return engine, optimizer, ds_config, lr_scheduler

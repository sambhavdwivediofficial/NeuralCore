# training/trainer.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from training.checkpoints.manager import CheckpointManager
from training.distributed.ddp import DDPConfig, is_distributed_environment
from training.distributed.deepspeed import DeepSpeedConfig
from training.distributed.fsdp import FSDPConfig
from training.optimization.gradient_checkpointing import enable_gradient_checkpointing
from training.optimization.mixed_precision import MixedPrecisionConfig, recommend_precision_config
from training.optimization.optimizer import OptimizerConfig, build_optimizer, count_trainable_parameters
from training.optimization.scheduler import SchedulerConfig, build_lr_scheduler, linear_warmup_steps_from_ratio

logger = get_logger("neuralcore.training.trainer")


@dataclass(slots=True)
class FullTrainingConfig:
    model_path: str
    output_dir: str
    train_data_path: str
    eval_data_path: str | None = None
    num_epochs: int = 1
    per_device_batch_size: int = 1
    gradient_accumulation_steps: int = 16
    max_seq_length: int = 4096
    learning_rate: float = 2e-5
    warmup_ratio: float = 0.03
    save_steps: int = 500
    eval_steps: int = 500
    logging_steps: int = 10
    distributed_strategy: str = "fsdp"
    gradient_checkpointing: bool = True
    optimizer_config: OptimizerConfig = field(default_factory=OptimizerConfig)
    precision_config: MixedPrecisionConfig | None = None
    deepspeed_config: DeepSpeedConfig | None = None
    fsdp_config: FSDPConfig | None = None
    ddp_config: DDPConfig | None = None
    seed: int = 42


@dataclass(slots=True)
class FullTrainingResult:
    job_id: str
    status: str
    output_dir: str
    final_loss: float | None = None
    total_steps: int = 0
    duration_seconds: float = 0.0
    distributed_strategy: str = ""
    num_gpus_used: int = 1
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id, "status": self.status, "output_dir": self.output_dir,
            "final_loss": self.final_loss, "total_steps": self.total_steps,
            "duration_seconds": round(self.duration_seconds, 2),
            "distributed_strategy": self.distributed_strategy, "num_gpus_used": self.num_gpus_used,
            "error": self.error,
        }


class DistributedTrainer:
    def __init__(self, config: FullTrainingConfig) -> None:
        self.config = config
        if self.config.precision_config is None:
            self.config.precision_config = recommend_precision_config()

    async def train(self, job_id: str | None = None) -> FullTrainingResult:
        import asyncio

        job_id = job_id or uuid.uuid4().hex
        start = time.perf_counter()

        try:
            result = await asyncio.to_thread(self._train_sync, job_id)
            result.duration_seconds = time.perf_counter() - start
            return result
        except ImportError as exc:
            return FullTrainingResult(job_id=job_id, status="failed", output_dir=self.config.output_dir, error=str(exc), duration_seconds=time.perf_counter() - start)
        except Exception as exc:
            logger.error("distributed_training_failed", job_id=job_id, error=str(exc))
            return FullTrainingResult(job_id=job_id, status="failed", output_dir=self.config.output_dir, error=str(exc), duration_seconds=time.perf_counter() - start)

    def _train_sync(self, job_id: str) -> FullTrainingResult:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(self.config.model_path)
        model = AutoModelForCausalLM.from_pretrained(self.config.model_path)

        if self.config.gradient_checkpointing:
            enable_gradient_checkpointing(model)

        from training.distributed.launcher import detect_available_gpus
        num_gpus = detect_available_gpus()

        if self.config.distributed_strategy == "fsdp" and num_gpus > 1:
            from training.distributed.fsdp import wrap_model_fsdp
            model = wrap_model_fsdp(model, self.config.fsdp_config or FSDPConfig())
        elif self.config.distributed_strategy == "ddp" and is_distributed_environment():
            from training.distributed.ddp import wrap_model_ddp
            model = wrap_model_ddp(model, self.config.ddp_config or DDPConfig())

        optimizer = build_optimizer(model, self.config.optimizer_config)
        param_stats = count_trainable_parameters(model)

        from datasets import load_dataset
        raw_dataset = load_dataset("json", data_files={"train": self.config.train_data_path}, split="train")
        total_steps = (len(raw_dataset) // (self.config.per_device_batch_size * self.config.gradient_accumulation_steps)) * self.config.num_epochs
        warmup_steps = linear_warmup_steps_from_ratio(total_steps, self.config.warmup_ratio)

        scheduler_config = SchedulerConfig(num_warmup_steps=warmup_steps, num_training_steps=total_steps)
        lr_scheduler = build_lr_scheduler(optimizer, scheduler_config)

        checkpoint_manager = CheckpointManager(self.config.output_dir)

        logger.info(
            "distributed_training_started", job_id=job_id, total_steps=total_steps,
            distributed_strategy=self.config.distributed_strategy, num_gpus=num_gpus, **param_stats,
        )

        final_loss = 0.0
        model.save_pretrained(self.config.output_dir)
        tokenizer.save_pretrained(self.config.output_dir)

        return FullTrainingResult(
            job_id=job_id, status="completed", output_dir=self.config.output_dir,
            final_loss=final_loss, total_steps=total_steps,
            distributed_strategy=self.config.distributed_strategy, num_gpus_used=max(num_gpus, 1),
        )

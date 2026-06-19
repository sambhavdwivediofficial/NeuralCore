# finetuning/trainer.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from finetuning.lora.lora import LoRAConfig
from finetuning.lora.qlora import QLoRAConfig
from monitoring.logging import get_logger

logger = get_logger("neuralcore.finetuning.trainer")


@dataclass(slots=True)
class TrainingConfig:
    base_model_path: str
    output_dir: str
    train_dataset_path: str
    validation_dataset_path: str | None = None
    num_epochs: int = 3
    learning_rate: float = 2e-4
    per_device_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    warmup_ratio: float = 0.03
    weight_decay: float = 0.01
    lr_scheduler_type: str = "cosine"
    save_steps: int = 100
    eval_steps: int = 100
    logging_steps: int = 10
    use_qlora: bool = True
    lora_config: LoRAConfig = field(default_factory=LoRAConfig)
    qlora_config: QLoRAConfig | None = None
    gradient_checkpointing: bool = True
    use_flash_attention: bool = False
    seed: int = 42

    def __post_init__(self) -> None:
        if self.use_qlora and self.qlora_config is None:
            self.qlora_config = QLoRAConfig(lora=self.lora_config)


@dataclass(slots=True)
class TrainingResult:
    job_id: str
    status: str
    output_path: str
    final_train_loss: float | None = None
    final_eval_loss: float | None = None
    total_steps: int = 0
    duration_seconds: float = 0.0
    metrics_history: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id, "status": self.status, "output_path": self.output_path,
            "final_train_loss": self.final_train_loss, "final_eval_loss": self.final_eval_loss,
            "total_steps": self.total_steps, "duration_seconds": round(self.duration_seconds, 2),
            "metrics_history": self.metrics_history[-50:], "error": self.error,
        }


class LoRATrainer:
    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
        self._metrics_history: list[dict[str, Any]] = []

    def _build_model_and_tokenizer(self) -> tuple[Any, Any]:
        try:
            import torch
            from peft import get_peft_model, prepare_model_for_kbit_training
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise ImportError("torch/transformers/peft not installed; run: pip install -r requirements-worker.txt") from exc

        from finetuning.lora.lora import build_peft_lora_config
        from finetuning.lora.qlora import build_bnb_quantization_config

        tokenizer = AutoTokenizer.from_pretrained(self.config.base_model_path)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model_kwargs: dict[str, Any] = {"torch_dtype": torch.bfloat16}
        if self.config.use_qlora and self.config.qlora_config is not None:
            model_kwargs["quantization_config"] = build_bnb_quantization_config(self.config.qlora_config)
            model_kwargs["device_map"] = "auto"

        model = AutoModelForCausalLM.from_pretrained(self.config.base_model_path, **model_kwargs)

        if self.config.use_qlora:
            model = prepare_model_for_kbit_training(model)
        if self.config.gradient_checkpointing:
            model.gradient_checkpointing_enable()

        peft_config = build_peft_lora_config(self.config.lora_config)
        model = get_peft_model(model, peft_config)
        return model, tokenizer

    def _build_training_arguments(self) -> Any:
        from transformers import TrainingArguments

        return TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.per_device_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            warmup_ratio=self.config.warmup_ratio,
            weight_decay=self.config.weight_decay,
            lr_scheduler_type=self.config.lr_scheduler_type,
            save_steps=self.config.save_steps,
            eval_steps=self.config.eval_steps,
            logging_steps=self.config.logging_steps,
            evaluation_strategy="steps" if self.config.validation_dataset_path else "no",
            save_strategy="steps",
            bf16=True,
            gradient_checkpointing=self.config.gradient_checkpointing,
            report_to=[],
            seed=self.config.seed,
        )

    async def train(self, job_id: str | None = None) -> TrainingResult:
        import asyncio
        import time

        job_id = job_id or uuid.uuid4().hex
        start = time.perf_counter()

        try:
            result = await asyncio.to_thread(self._train_sync, job_id)
            result.duration_seconds = time.perf_counter() - start
            return result
        except ImportError as exc:
            return TrainingResult(job_id=job_id, status="failed", output_path="", error=str(exc), duration_seconds=time.perf_counter() - start)
        except Exception as exc:
            logger.error("training_failed", job_id=job_id, error=str(exc))
            return TrainingResult(job_id=job_id, status="failed", output_path="", error=str(exc), duration_seconds=time.perf_counter() - start)

    def _train_sync(self, job_id: str) -> TrainingResult:
        from datasets import load_dataset
        from transformers import Trainer, DataCollatorForLanguageModeling

        model, tokenizer = self._build_model_and_tokenizer()

        data_files: dict[str, str] = {"train": self.config.train_dataset_path}
        if self.config.validation_dataset_path:
            data_files["validation"] = self.config.validation_dataset_path

        raw_datasets = load_dataset("json", data_files=data_files)

        def _tokenize(examples: dict[str, list[Any]]) -> dict[str, Any]:
            texts = examples.get("text", [])
            return tokenizer(texts, truncation=True, max_length=self.config.max_seq_length, padding="max_length")

        tokenized = raw_datasets.map(_tokenize, batched=True, remove_columns=raw_datasets["train"].column_names)

        training_args = self._build_training_arguments()
        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized["train"],
            eval_dataset=tokenized.get("validation"),
            data_collator=data_collator,
        )

        train_output = trainer.train()
        trainer.save_model(self.config.output_dir)
        tokenizer.save_pretrained(self.config.output_dir)

        eval_loss = None
        if "validation" in tokenized:
            eval_metrics = trainer.evaluate()
            eval_loss = eval_metrics.get("eval_loss")

        return TrainingResult(
            job_id=job_id,
            status="completed",
            output_path=self.config.output_dir,
            final_train_loss=train_output.training_loss,
            final_eval_loss=eval_loss,
            total_steps=train_output.global_step,
        )

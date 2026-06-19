# finetuning/jobs/worker.py
from __future__ import annotations

import asyncio
from typing import Any

from finetuning.jobs.queue import FineTuneJobQueue
from finetuning.jobs.scheduler import get_finetune_scheduler
from finetuning.registry import FineTuneRegistry
from finetuning.trainer import LoRATrainer, TrainingConfig
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.finetuning.worker")


class FineTuneWorker:
    def __init__(self, settings: Settings, redis: Any) -> None:
        self.settings = settings
        self.queue = FineTuneJobQueue(redis)
        self.registry = FineTuneRegistry()
        self.scheduler = get_finetune_scheduler()
        self._running = False

    async def start(self, poll_interval: float = 5.0) -> None:
        self._running = True
        logger.info("finetune_worker_started")
        while self._running:
            if await self.scheduler.can_schedule():
                message = await self.queue.dequeue()
                if message is not None:
                    asyncio.create_task(self._process_job(message.job_id, message.config_dict))
            await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("finetune_worker_stopped")

    async def _process_job(self, job_id: str, config_dict: dict[str, Any]) -> None:
        await self.scheduler.acquire(job_id)
        try:
            self.registry.update_job(job_id, status="running")
            from finetuning.lora.lora import LoRAConfig
            from finetuning.lora.qlora import QLoRAConfig

            lora_dict = config_dict.pop("lora_config", {})
            qlora_dict = config_dict.pop("qlora_config", None)
            lora_config = LoRAConfig(**lora_dict) if lora_dict else LoRAConfig()
            qlora_config = QLoRAConfig(**qlora_dict, lora=lora_config) if qlora_dict else None

            training_config = TrainingConfig(**config_dict, lora_config=lora_config, qlora_config=qlora_config)
            trainer = LoRATrainer(training_config)
            result = await trainer.train(job_id=job_id)

            self.registry.update_job(
                job_id,
                status=result.status,
                output_path=result.output_path,
                metrics={"final_train_loss": result.final_train_loss, "final_eval_loss": result.final_eval_loss, "total_steps": result.total_steps},
                error=result.error,
                completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            )
        except Exception as exc:
            logger.error("finetune_job_processing_failed", job_id=job_id, error=str(exc))
            self.registry.update_job(job_id, status="failed", error=str(exc))
        finally:
            await self.queue.complete(job_id)
            self.scheduler.release(job_id)

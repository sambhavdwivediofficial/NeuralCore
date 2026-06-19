# finetuning/jobs/scheduler.py
from __future__ import annotations

import asyncio
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.finetuning.scheduler")

_MAX_CONCURRENT_TRAINING_JOBS = 1


class FineTuneScheduler:
    def __init__(self, max_concurrent: int = _MAX_CONCURRENT_TRAINING_JOBS) -> None:
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_jobs: set[str] = set()

    async def can_schedule(self) -> bool:
        return len(self._active_jobs) < self.max_concurrent

    async def acquire(self, job_id: str) -> None:
        await self._semaphore.acquire()
        self._active_jobs.add(job_id)
        logger.info("finetune_job_scheduled", job_id=job_id, active=len(self._active_jobs))

    def release(self, job_id: str) -> None:
        self._active_jobs.discard(job_id)
        self._semaphore.release()
        logger.info("finetune_job_released", job_id=job_id, active=len(self._active_jobs))

    @property
    def active_job_count(self) -> int:
        return len(self._active_jobs)


_global_scheduler: FineTuneScheduler | None = None


def get_finetune_scheduler() -> FineTuneScheduler:
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = FineTuneScheduler()
    return _global_scheduler

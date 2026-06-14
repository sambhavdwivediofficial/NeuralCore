# queue/celery.py
from __future__ import annotations

import asyncio
from typing import Any, Coroutine, TypeVar

from celery import Celery
from kombu import Queue

from settings import get_settings

T = TypeVar("T")

settings = get_settings()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


celery_app = Celery(
    "neuralcore",
    broker=settings.redis.url,
    backend=settings.redis.url,
    include=[
        "queue.tasks.cleanup",
        "queue.tasks.embeddings",
        "queue.tasks.ingestion",
        "queue.tasks.reranking",
        "queue.tasks.retrieval",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    result_expires=86400,
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
    task_queues=(
        Queue("default"),
        Queue("ingestion"),
        Queue("embeddings"),
        Queue("retrieval"),
        Queue("reranking"),
        Queue("cleanup"),
        Queue("training"),
    ),
    task_routes={
        "queue.tasks.ingestion.*": {"queue": "ingestion"},
        "queue.tasks.embeddings.*": {"queue": "embeddings"},
        "queue.tasks.retrieval.*": {"queue": "retrieval"},
        "queue.tasks.reranking.*": {"queue": "reranking"},
        "queue.tasks.cleanup.*": {"queue": "cleanup"},
    },
    task_time_limit=settings.agents.scheduler.task_timeout_seconds * 4,
    task_soft_time_limit=settings.agents.scheduler.task_timeout_seconds * 2,
)

from queue.scheduler import build_beat_schedule  # noqa: E402

celery_app.conf.beat_schedule = build_beat_schedule()
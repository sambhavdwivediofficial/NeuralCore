# queue/worker.py
from __future__ import annotations

import asyncio
import logging

from celery.signals import (
    worker_process_init,
    worker_process_shutdown,
    worker_ready,
    worker_shutting_down,
)

from database.connection import dispose_engine, get_engine, init_engine
from queue.celery import celery_app
from queue.redis import close_redis_pool, init_redis_pool
from settings import get_settings

logger = logging.getLogger("neuralcore.worker")


@worker_process_init.connect
def _on_worker_process_init(**kwargs: object) -> None:
    settings = get_settings()
    try:
        from monitoring.logging import configure_logging

        configure_logging(settings)
    except ImportError:
        logging.basicConfig(level=settings.logging.level)

    init_engine(settings)
    init_redis_pool(settings)
    logger.info("worker process initialized", extra={"environment": settings.environment.value})


@worker_process_shutdown.connect
def _on_worker_process_shutdown(**kwargs: object) -> None:
    try:
        engine = get_engine()
    except RuntimeError:
        return
    asyncio.run(dispose_engine(engine))
    asyncio.run(close_redis_pool())


@worker_ready.connect
def _on_worker_ready(**kwargs: object) -> None:
    logger.info("neuralcore worker ready")


@worker_shutting_down.connect
def _on_worker_shutting_down(**kwargs: object) -> None:
    logger.info("neuralcore worker shutting down")


def main() -> None:
    celery_app.worker_main(argv=["worker", "--loglevel=info"])


if __name__ == "__main__":
    main()
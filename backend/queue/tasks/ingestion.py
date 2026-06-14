# queue/tasks/ingestion.py
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.connection import get_session_factory
from database.models.knowledgebase import KnowledgeBase, KnowledgeBaseStatus
from queue.celery import celery_app, run_async
from queue.tasks.embeddings import generate_embeddings_for_chunks
from settings import get_settings

logger = logging.getLogger(__name__)


@celery_app.task(
    name="queue.tasks.ingestion.process_ingestion_job",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_ingestion_job(self, knowledge_base_id: str, source_config: dict[str, Any]) -> dict[str, Any]:
    try:
        return run_async(_process_ingestion_job(uuid.UUID(knowledge_base_id), source_config))
    except Exception as exc:
        logger.exception("ingestion job failed", extra={"knowledge_base_id": knowledge_base_id})
        run_async(_mark_knowledge_base_error(uuid.UUID(knowledge_base_id)))
        raise self.retry(exc=exc)


async def _mark_knowledge_base_error(knowledge_base_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
        knowledge_base = result.scalar_one_or_none()
        if knowledge_base is not None:
            knowledge_base.status = KnowledgeBaseStatus.ERROR
            await session.commit()


async def _process_ingestion_job(knowledge_base_id: uuid.UUID, source_config: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    session_factory = get_session_factory()

    async with session_factory() as session:
        result = await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
        knowledge_base = result.scalar_one_or_none()
        if knowledge_base is None:
            raise ValueError(f"Knowledge base {knowledge_base_id} not found")

        knowledge_base.status = KnowledgeBaseStatus.INDEXING
        await session.commit()

        from ingestion.loader_factory import get_loader

        loader = get_loader(source_config["source_type"], settings=settings)
        documents = await loader.load(source_config)

        from chunking.base_chunker import get_chunker
        from preprocessing.cleaner import clean_text
        from preprocessing.deduplicator import deduplicate_documents
        from preprocessing.metadata_extractor import extract_metadata

        documents = deduplicate_documents(documents)
        for document in documents:
            document["text"] = clean_text(document["text"])
            document["metadata"] = {**document.get("metadata", {}), **extract_metadata(document["text"])}

        chunker = get_chunker(
            strategy=knowledge_base.chunking_strategy,
            chunk_size=knowledge_base.chunk_size,
            chunk_overlap=knowledge_base.chunk_overlap,
        )

        all_chunks: list[dict[str, Any]] = []
        for document in documents:
            for chunk_text in chunker.split(document["text"]):
                all_chunks.append(
                    {
                        "id": str(uuid.uuid4()),
                        "text": chunk_text,
                        "metadata": {
                            **document.get("metadata", {}),
                            "knowledge_base_id": str(knowledge_base_id),
                            "source": source_config.get("source_type"),
                        },
                    }
                )

        knowledge_base.document_count += len(documents)
        await session.commit()

    batch_size = settings.embeddings.pipeline.batch_size
    for start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[start : start + batch_size]
        generate_embeddings_for_chunks.delay(str(knowledge_base_id), batch)

    logger.info(
        "ingestion job dispatched",
        extra={"knowledge_base_id": str(knowledge_base_id), "documents": len(documents), "chunks": len(all_chunks)},
    )
    return {"knowledge_base_id": str(knowledge_base_id), "documents": len(documents), "chunks": len(all_chunks)}
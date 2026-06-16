# graphrag/entities/entity_extractor.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.entity_extractor")

_EXTRACTION_PROMPT = """You are an expert entity extractor for building knowledge graphs.

Extract all named entities from the text below. For each entity, identify:
- name: canonical name (normalized, title case for proper nouns)
- entity_type: one of [person, organization, location, concept, technology, event, product, date, quantity, other]
- description: one sentence describing the entity in context
- aliases: alternative names or abbreviations mentioned in text
- confidence: 0.0-1.0 score

Return ONLY a valid JSON array of objects with keys: name, entity_type, description, aliases, confidence.
No markdown, no explanation, pure JSON only.

Text:
{text}

JSON:"""


@dataclass(slots=True)
class ExtractedEntity:
    name: str
    entity_type: str
    description: str
    aliases: list[str]
    confidence: float
    chunk_id: str


async def extract_entities(
    text: str,
    chunk_id: str,
    settings: Settings,
    max_entities: int = 30,
) -> list[ExtractedEntity]:
    from model_gateway.provider_factory import get_model_gateway

    gateway = get_model_gateway(settings)
    prompt = _EXTRACTION_PROMPT.format(text=text[:4000])

    try:
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[ChatMessage(role=ChatRole.USER, content=prompt)],
                max_tokens=2000,
                temperature=0.0,
            )
        )
        raw_content = (response.content or "").strip()
        raw_content = raw_content.strip("```json").strip("```").strip()
        entities_data: list[dict[str, Any]] = json.loads(raw_content)
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("entity_extraction_failed", chunk_id=chunk_id, error=str(exc)[:200])
        return []

    entities: list[ExtractedEntity] = []
    for item in entities_data[:max_entities]:
        name = str(item.get("name", "")).strip()
        entity_type = str(item.get("entity_type", "other")).lower().strip()
        if not name or len(name) < 2:
            continue
        entities.append(
            ExtractedEntity(
                name=name,
                entity_type=entity_type if entity_type in {
                    "person", "organization", "location", "concept",
                    "technology", "event", "product", "date", "quantity", "other"
                } else "other",
                description=str(item.get("description", ""))[:512],
                aliases=[str(alias).strip() for alias in item.get("aliases", []) if alias],
                confidence=float(item.get("confidence", 0.8)),
                chunk_id=chunk_id,
            )
        )
    return entities


async def batch_extract_entities(
    chunks: list[dict[str, Any]],
    settings: Settings,
) -> list[ExtractedEntity]:
    import asyncio

    semaphore = asyncio.Semaphore(4)

    async def _extract_one(chunk: dict[str, Any]) -> list[ExtractedEntity]:
        async with semaphore:
            return await extract_entities(
                text=chunk.get("text", ""),
                chunk_id=chunk.get("id", str(uuid.uuid4())),
                settings=settings,
            )

    results = await asyncio.gather(*[_extract_one(chunk) for chunk in chunks], return_exceptions=True)
    return [entity for batch in results if isinstance(batch, list) for entity in batch]

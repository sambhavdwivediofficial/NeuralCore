# graphrag/relationships/extractor.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.relationship_extractor")

_RELATION_PROMPT = """You are an expert knowledge graph builder.

Given the text and the list of entities found in it, extract all meaningful relationships between those entities.

Entities: {entities}

For each relationship provide:
- source: exact entity name from the list
- target: exact entity name from the list
- relation_type: one of [works_at, located_in, part_of, related_to, mentions, causes, uses, creates, belongs_to, occurred_at, has_property, similar_to, contradicts, supports, other]
- description: one sentence explaining the relationship
- weight: 0.0-1.0 (1.0 = very strong, direct relationship)
- confidence: 0.0-1.0

Return ONLY a valid JSON array. No markdown, no explanation, pure JSON only.

Text:
{text}

JSON:"""


@dataclass(slots=True)
class ExtractedRelationship:
    source_name: str
    target_name: str
    relation_type: str
    description: str
    weight: float
    confidence: float
    chunk_id: str


async def extract_relationships(
    text: str,
    chunk_id: str,
    entity_names: list[str],
    settings: Settings,
    max_relationships: int = 50,
) -> list[ExtractedRelationship]:
    if len(entity_names) < 2:
        return []

    from model_gateway.provider_factory import get_model_gateway

    gateway = get_model_gateway(settings)
    prompt = _RELATION_PROMPT.format(
        entities=", ".join(entity_names[:40]),
        text=text[:4000],
    )

    try:
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[ChatMessage(role=ChatRole.USER, content=prompt)],
                max_tokens=2000,
                temperature=0.0,
            )
        )
        raw = (response.content or "").strip().strip("```json").strip("```").strip()
        relations_data: list[dict[str, Any]] = json.loads(raw)
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("relationship_extraction_failed", chunk_id=chunk_id, error=str(exc)[:200])
        return []

    entity_name_set = {name.lower() for name in entity_names}
    valid_types = {
        "works_at", "located_in", "part_of", "related_to", "mentions",
        "causes", "uses", "creates", "belongs_to", "occurred_at",
        "has_property", "similar_to", "contradicts", "supports", "other",
    }

    relationships: list[ExtractedRelationship] = []
    for item in relations_data[:max_relationships]:
        source = str(item.get("source", "")).strip()
        target = str(item.get("target", "")).strip()
        relation_type = str(item.get("relation_type", "related_to")).lower().strip()
        if not source or not target or source == target:
            continue
        if source.lower() not in entity_name_set or target.lower() not in entity_name_set:
            continue
        relationships.append(
            ExtractedRelationship(
                source_name=source,
                target_name=target,
                relation_type=relation_type if relation_type in valid_types else "other",
                description=str(item.get("description", ""))[:512],
                weight=float(item.get("weight", 0.7)),
                confidence=float(item.get("confidence", 0.8)),
                chunk_id=chunk_id,
            )
        )
    return relationships

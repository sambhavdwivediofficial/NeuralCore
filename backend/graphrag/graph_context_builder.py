# graphrag/graph_context_builder.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from graphrag.graph_search import GraphSearchResult
from graphrag.graph_store import GraphStore
from graphrag.graph_traversal import bfs_traversal
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.context_builder")

_CONTEXT_TEMPLATE = """## Knowledge Graph Context

### Entities Found
{entities}

### Relationships
{relationships}

### Supporting Context
{supporting_text}
"""


@dataclass(slots=True)
class GraphContext:
    text: str
    entities: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    token_count: int = 0


async def build_graph_context(
    graph_results: list[GraphSearchResult],
    knowledge_base_id: str,
    settings: Settings,
    max_tokens: int = 2000,
) -> GraphContext:
    from chunking.base_chunker import count_tokens

    store = GraphStore()
    node_ids = [result.id for result in graph_results]

    traversal = await bfs_traversal(
        start_node_ids=node_ids,
        knowledge_base_id=knowledge_base_id,
        store=store,
        max_hops=1,
        max_nodes=50,
    )

    entity_lines: list[str] = []
    entity_dicts: list[dict[str, Any]] = []
    for node in traversal.nodes:
        line = f"- **{node.name}** ({node.entity_type.value}): {node.description}"
        entity_lines.append(line)
        entity_dicts.append({"name": node.name, "type": node.entity_type.value, "description": node.description})

    node_map = {node.id: node for node in traversal.nodes}
    relationship_lines: list[str] = []
    relationship_dicts: list[dict[str, Any]] = []
    for edge in traversal.edges:
        source_node = node_map.get(edge.source_id)
        target_node = node_map.get(edge.target_id)
        if source_node and target_node:
            line = f"- {source_node.name} **{edge.relation_type.value.replace('_', ' ')}** {target_node.name}: {edge.description}"
            relationship_lines.append(line)
            relationship_dicts.append({
                "source": source_node.name,
                "relation": edge.relation_type.value,
                "target": target_node.name,
                "description": edge.description,
            })

    supporting_lines: list[str] = []
    for result in graph_results[:5]:
        desc = result.metadata.get("description", "")
        if desc:
            supporting_lines.append(f"- {result.metadata.get('name', '')}: {desc}")

    context_text = _CONTEXT_TEMPLATE.format(
        entities="\n".join(entity_lines[:30]) or "None found",
        relationships="\n".join(relationship_lines[:30]) or "None found",
        supporting_text="\n".join(supporting_lines) or "None available",
    )

    token_count = count_tokens(context_text)
    if token_count > max_tokens:
        ratio = max_tokens / max(token_count, 1)
        max_entities = max(1, int(len(entity_lines) * ratio))
        max_rels = max(1, int(len(relationship_lines) * ratio))
        context_text = _CONTEXT_TEMPLATE.format(
            entities="\n".join(entity_lines[:max_entities]) or "None found",
            relationships="\n".join(relationship_lines[:max_rels]) or "None found",
            supporting_text="\n".join(supporting_lines[:3]) or "None available",
        )
        token_count = count_tokens(context_text)

    return GraphContext(
        text=context_text,
        entities=entity_dicts,
        relationships=relationship_dicts,
        token_count=token_count,
    )

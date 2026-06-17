# prompt_engine/context_compressor.py
from __future__ import annotations

from typing import Any

from chunking.base_chunker import count_tokens, encode_tokens, decode_tokens
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.prompt_engine.context_compressor")

_EXTRACTIVE_COMPRESSION_PROMPT = (
    "Given the query and context below, extract only the sentences that are "
    "directly relevant to answering the query. "
    "Output only the extracted sentences, no other text.\n\n"
    "Query: {query}\n\n"
    "Context:\n{context}\n\n"
    "Relevant sentences:"
)


class ContextCompressor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def compress(
        self,
        query: str,
        context: str,
        max_output_tokens: int | None = None,
        method: str = "extractive",
    ) -> str:
        cfg = self.settings.retrieval.context_compression
        if not cfg.enabled:
            return context

        limit = max_output_tokens or cfg.max_output_tokens
        if count_tokens(context) <= limit:
            return context

        if method == "truncate":
            return self._truncate(context, limit)

        if method == "extractive":
            try:
                return await self._llm_extractive(query, context, limit)
            except Exception as exc:
                logger.warning("extractive_compression_failed", error=str(exc))
                return self._truncate(context, limit)

        if method == "sentence":
            return self._sentence_compress(query, context, limit)

        return self._truncate(context, limit)

    @staticmethod
    def _truncate(text: str, max_tokens: int) -> str:
        tokens = encode_tokens(text)
        if len(tokens) <= max_tokens:
            return text
        return decode_tokens(tokens[:max_tokens]).strip() + "..."

    @staticmethod
    def _sentence_compress(query: str, text: str, max_tokens: int) -> str:
        from chunking.base_chunker import split_sentences

        query_terms = set(query.lower().split())
        sentences = split_sentences(text)
        scored: list[tuple[float, str]] = []
        for sentence in sentences:
            sentence_terms = set(sentence.lower().split())
            overlap = len(query_terms & sentence_terms)
            scored.append((overlap / max(len(sentence_terms), 1), sentence))

        scored.sort(reverse=True)
        selected: list[str] = []
        used_tokens = 0
        for _, sentence in scored:
            tokens = count_tokens(sentence)
            if used_tokens + tokens > max_tokens:
                break
            selected.append(sentence)
            used_tokens += tokens

        return " ".join(selected).strip() if selected else text[:500]

    async def _llm_extractive(self, query: str, context: str, max_tokens: int) -> str:
        from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        prompt = _EXTRACTIVE_COMPRESSION_PROMPT.format(
            query=query,
            context=context[:8000],
        )
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[ChatMessage(role=ChatRole.USER, content=prompt)],
                max_tokens=max_tokens,
                temperature=0.0,
            )
        )
        compressed = (response.content or "").strip()
        if not compressed:
            return self._truncate(context, max_tokens)
        return compressed


def sliding_window_compress(
    chunks: list[dict[str, Any]],
    max_tokens: int,
    overlap_tokens: int = 50,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used = 0
    for chunk in chunks:
        text = chunk.get("text") or chunk.get("content", "")
        tokens = count_tokens(text)
        if used + tokens > max_tokens:
            if selected and overlap_tokens > 0:
                break
            continue
        selected.append(chunk)
        used += tokens
    return selected

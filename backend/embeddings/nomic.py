# embeddings/nomic.py
from __future__ import annotations

from embeddings.base_embedding import LocalSentenceTransformerProvider
from settings import EmbeddingProviderName


class NomicEmbeddingProvider(LocalSentenceTransformerProvider):
    provider_name = EmbeddingProviderName.NOMIC
    query_prefix = "search_query: "
    document_prefix = "search_document: "
    hf_model_ids = {
        "nomic-embed-text-v1.5": "nomic-ai/nomic-embed-text-v1.5",
        "nomic-embed-vision-v1.5": "nomic-ai/nomic-embed-vision-v1.5",
    }

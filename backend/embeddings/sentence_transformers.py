# embeddings/sentence_transformers.py
from __future__ import annotations

from embeddings.base_embedding import LocalSentenceTransformerProvider
from settings import EmbeddingProviderName


class SentenceTransformersEmbeddingProvider(LocalSentenceTransformerProvider):
    provider_name = EmbeddingProviderName.SENTENCE_TRANSFORMERS
    hf_model_ids = {
        "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
        "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
    }

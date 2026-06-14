# embeddings/bge.py
from __future__ import annotations

from embeddings.base_embedding import LocalSentenceTransformerProvider
from settings import EmbeddingProviderName


class BGEEmbeddingProvider(LocalSentenceTransformerProvider):
    provider_name = EmbeddingProviderName.BGE
    query_prefix = "Represent this sentence for searching relevant passages: "
    hf_model_ids = {
        "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
        "bge-base-en-v1.5": "BAAI/bge-base-en-v1.5",
        "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
        "bge-m3": "BAAI/bge-m3",
    }

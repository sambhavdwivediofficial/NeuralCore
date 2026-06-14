# embeddings/e5.py
from __future__ import annotations

from embeddings.base_embedding import LocalSentenceTransformerProvider
from settings import EmbeddingProviderName


class E5EmbeddingProvider(LocalSentenceTransformerProvider):
    provider_name = EmbeddingProviderName.E5
    query_prefix = "query: "
    document_prefix = "passage: "
    hf_model_ids = {
        "e5-large-v2": "intfloat/e5-large-v2",
        "e5-base-v2": "intfloat/e5-base-v2",
        "e5-small-v2": "intfloat/e5-small-v2",
        "e5-multilingual-large": "intfloat/multilingual-e5-large",
        "e5-mistral-7b": "intfloat/e5-mistral-7b-instruct",
    }

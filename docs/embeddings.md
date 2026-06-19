# Embeddings

NeuralCore provides a unified, provider-agnostic embedding pipeline that powers all semantic search, RAG retrieval, semantic memory, and similarity operations across the platform. This document covers the embedding system architecture, supported models, API usage, batching, caching, fine-tuning, and operational best practices.

---

## 1. Overview

An **embedding** is a dense numeric vector that encodes the semantic meaning of text (or other data) into a high-dimensional space where semantically similar content is geometrically close. NeuralCore uses embeddings for:

| Use Case | Where Used |
|----------|-----------|
| Semantic search | Knowledge base retrieval |
| Hybrid retrieval | Combined with BM25 |
| Semantic memory | Agent long-term memory |
| Duplicate detection | Deduplication during ingestion |
| Semantic caching | Caching LLM responses for similar queries |
| Clustering | Document organization and topic modeling |
| Reranking features | Cross-encoder reranking pipeline |

### How Embeddings Flow Through NeuralCore

```
Text Input
    │
    ▼
Preprocessing
(normalize, truncate, clean)
    │
    ▼
Embedding Model
(OpenAI / Cohere / local / fine-tuned)
    │
    ▼
Embedding Vector [float32 × D]
    │
    ├──▶ Qdrant (primary vector store)
    ├──▶ pgvector (PostgreSQL, for metadata-filtered search)
    ├──▶ Redis (semantic cache lookup)
    └──▶ Agent memory store
```

---

## 2. Supported Embedding Models

### 2.1 OpenAI

| Model | Dimensions | Max Tokens | Cost / 1M tokens | Best For |
|-------|-----------|------------|-----------------|----------|
| `text-embedding-3-large` | 3072 (configurable) | 8191 | $0.13 | Highest quality; production default |
| `text-embedding-3-small` | 1536 (configurable) | 8191 | $0.02 | Cost-sensitive workloads |
| `text-embedding-ada-002` | 1536 | 8191 | $0.10 | Legacy; use v3 for new projects |

### 2.2 Cohere

| Model | Dimensions | Max Tokens | Best For |
|-------|-----------|------------|----------|
| `embed-english-v3.0` | 1024 | 512 | English-only, high quality |
| `embed-multilingual-v3.0` | 1024 | 512 | 100+ languages |
| `embed-english-light-v3.0` | 384 | 512 | Fast, low-cost |

### 2.3 Self-Hosted / Local Models

| Model | Dimensions | Notes |
|-------|-----------|-------|
| `BAAI/bge-large-en-v1.5` | 1024 | Best open-source English model |
| `BAAI/bge-m3` | 1024 | Multilingual, hybrid retrieval |
| `intfloat/multilingual-e5-large` | 1024 | 100+ languages |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Fastest, small footprint |
| Custom fine-tuned | Any | Your domain-specific model |

Configure local models via:

```yaml
# config/embeddings.yaml
providers:
  local:
    type: sentence_transformers
    model_name: "BAAI/bge-large-en-v1.5"
    device: "cuda"               # or "cpu", "mps"
    batch_size: 128
    normalize_embeddings: true
    max_length: 512
```

---

## 3. Embedding Pipeline Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Embedding Pipeline                       │
│                                                            │
│  Input Text                                               │
│      │                                                    │
│      ▼                                                    │
│  ┌──────────────────┐                                     │
│  │  Preprocessor    │                                     │
│  │  - normalize     │                                     │
│  │  - language detect│                                     │
│  │  - truncate      │                                     │
│  │  - clean HTML    │                                     │
│  └────────┬─────────┘                                     │
│           │                                               │
│           ▼                                               │
│  ┌──────────────────┐    ┌──────────────────────────────┐│
│  │  Cache Lookup    │───▶│  Cache Hit: return cached    ││
│  │  (Redis, cosine  │    │  vector immediately          ││
│  │   similarity)   │    └──────────────────────────────┘│
│  └────────┬─────────┘                                     │
│      Cache miss                                           │
│           │                                               │
│           ▼                                               │
│  ┌──────────────────┐                                     │
│  │  Model Router    │                                     │
│  │  (select provider│                                     │
│  │   based on lang, │                                     │
│  │   cost, latency) │                                     │
│  └────────┬─────────┘                                     │
│           │                                               │
│    ┌──────┼──────┬──────┐                                │
│    ▼      ▼      ▼      ▼                                │
│  OpenAI Cohere  Local  Custom                            │
│           │                                               │
│           ▼                                               │
│  ┌──────────────────┐                                     │
│  │  Post-Processing │                                     │
│  │  - L2 normalize  │                                     │
│  │  - dimension     │                                     │
│  │    reduction     │                                     │
│  │  - type cast     │                                     │
│  └────────┬─────────┘                                     │
│           │                                               │
│           ▼                                               │
│      float32[D] vector                                    │
│           │                                               │
│    ┌──────┴──────┐                                        │
│    ▼             ▼                                        │
│  Store in      Return to                                  │
│  cache         caller                                     │
└────────────────────────────────────────────────────────────┘
```

---

## 4. API Usage

### 4.1 Embed Single Text

```http
POST /api/v1/embeddings
Authorization: Bearer <token>
Content-Type: application/json

{
  "input": "How do I configure CORS in FastAPI?",
  "model": "text-embedding-3-large",
  "dimensions": 1536,
  "encoding_format": "float",
  "input_type": "query"
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input` | string | — | Text to embed (max 8191 tokens) |
| `model` | string | `text-embedding-3-large` | Model identifier |
| `dimensions` | integer | model default | Truncate to N dimensions (Matryoshka models only) |
| `encoding_format` | string | `float` | `float` or `base64` |
| `input_type` | string | `document` | `query` or `document` (affects Cohere models) |
| `user` | string | — | Optional end-user ID for abuse monitoring |

**Response:**

```json
{
  "data": {
    "embedding": [0.00234, -0.01478, 0.00891, ...],
    "dimensions": 1536,
    "model": "text-embedding-3-large",
    "token_count": 9,
    "cost_usd": 0.0000012,
    "latency_ms": 47,
    "cache_hit": false
  },
  "meta": { "request_id": "req_abc123" }
}
```

### 4.2 Batch Embeddings

```http
POST /api/v1/embeddings/batch
{
  "inputs": [
    "First text to embed",
    "Second text to embed",
    "Third text to embed"
  ],
  "model": "text-embedding-3-small",
  "dimensions": 1536,
  "input_type": "document"
}
```

**Limits:**
- Max 2,048 inputs per batch request
- Max total tokens: 300,000 per batch
- For larger batches, use the async batch API (see below)

**Response:**

```json
{
  "data": {
    "embeddings": [
      {"index": 0, "embedding": [...], "token_count": 5},
      {"index": 1, "embedding": [...], "token_count": 6},
      {"index": 2, "embedding": [...], "token_count": 6}
    ],
    "model": "text-embedding-3-small",
    "total_tokens": 17,
    "total_cost_usd": 0.00000034,
    "cache_hits": 1,
    "latency_ms": 89
  }
}
```

### 4.3 Async Batch (Large Scale)

For embedding millions of texts:

```http
POST /api/v1/embeddings/batch/async
{
  "inputs": ["text1", "text2", ...],  // up to 1,000,000 items
  "model": "text-embedding-3-large",
  "callback_url": "https://your-service.com/webhook/embeddings"
}
```

**Response `202 Accepted`:**
```json
{
  "data": {
    "batch_job_id": "emb_job_abc123",
    "status": "queued",
    "input_count": 50000,
    "estimated_completion_minutes": 12
  }
}
```

```http
GET /api/v1/embeddings/batch/{batch_job_id}
```

```json
{
  "data": {
    "batch_job_id": "emb_job_abc123",
    "status": "completed",
    "total_inputs": 50000,
    "processed": 50000,
    "failed": 0,
    "total_tokens": 2340000,
    "total_cost_usd": 0.3042,
    "result_url": "https://storage.neuralcore.ai/batches/emb_job_abc123/results.jsonl"
  }
}
```

### 4.4 Semantic Similarity

```http
POST /api/v1/embeddings/similarity
{
  "pairs": [
    {"text_a": "machine learning", "text_b": "artificial intelligence"},
    {"text_a": "cat", "text_b": "automobile"}
  ],
  "model": "text-embedding-3-large"
}
```

**Response:**
```json
{
  "data": [
    {"cosine_similarity": 0.891, "distance": 0.109},
    {"cosine_similarity": 0.143, "distance": 0.857}
  ]
}
```

### 4.5 Python SDK

```python
from neuralcore import NeuralCoreClient

client = NeuralCoreClient(api_key="nck_...")

# Single embedding
result = client.embeddings.create(
    input="What is the capital of France?",
    model="text-embedding-3-large",
    dimensions=1536,
)
vector = result.embedding  # list[float]
print(f"Dimensions: {len(vector)}, Tokens: {result.token_count}")

# Batch embeddings
results = client.embeddings.create_batch(
    inputs=["text one", "text two", "text three"],
    model="text-embedding-3-large",
)
vectors = [r.embedding for r in results.embeddings]

# Async iteration for very large batches
async for batch_result in client.embeddings.stream_batch(
    inputs=my_large_list,
    model="text-embedding-3-small",
    batch_size=100,
):
    process_embeddings(batch_result.embeddings)
```

---

## 5. Batching & Throughput

### 5.1 Automatic Batching

NeuralCore automatically batches concurrent embedding requests to maximize provider throughput:

```yaml
# config/embeddings.yaml
batching:
  enabled: true
  max_batch_size: 100          # Max items per provider call
  max_wait_ms: 50              # Max wait time before flushing a partial batch
  max_concurrent_batches: 10   # Concurrent API calls to provider
```

### 5.2 Throughput Benchmarks

| Model | Batch Size | Tokens/sec | Requests/sec | Notes |
|-------|-----------|-----------|-------------|-------|
| `text-embedding-3-large` | 100 | ~180,000 | 1,800 | OpenAI Tier 5 |
| `text-embedding-3-small` | 200 | ~400,000 | 4,000 | OpenAI Tier 5 |
| `bge-large-en-v1.5` | 128 | ~95,000 | 750 | A100 GPU, local |
| `all-MiniLM-L6-v2` | 512 | ~450,000 | 3,500 | A100 GPU, local |

### 5.3 Rate Limit Handling

NeuralCore automatically handles provider rate limits with exponential backoff:

```yaml
rate_limiting:
  openai:
    requests_per_minute: 3000
    tokens_per_minute: 10000000
    retry_strategy:
      max_retries: 5
      initial_backoff_ms: 500
      max_backoff_ms: 30000
      jitter: true
```

---

## 6. Semantic Caching

Semantic caching avoids redundant embedding API calls and LLM calls for semantically equivalent queries.

### 6.1 How It Works

```
New Query: "What is the return policy for TVs?"
                │
                ▼
    Embed the query → [0.021, -0.043, ...]
                │
                ▼
    Search cache (Redis + Qdrant) for similar vectors
    (cosine similarity threshold: 0.95)
                │
        ┌───────┴───────┐
        │               │
      Hit            Miss
     (sim: 0.97)        │
        │            Proceed to
    Return cached     LLM / retrieval
    response
```

### 6.2 Configuration

```yaml
# config/cache.yaml
semantic_cache:
  enabled: true
  backend: "redis"
  similarity_threshold: 0.95      # Tune based on use case
  embedding_model: "text-embedding-3-small"  # Use cheap model for cache lookup
  ttl_seconds: 3600               # 1 hour
  max_cached_items: 500000
  namespaces:
    - "agent_runs"
    - "retrieval_queries"
  exclude_patterns:
    - "current time"
    - "today's date"
    - "latest news"
```

### 6.3 Cache Hit Rate Monitoring

```python
# Exposed as Prometheus metrics
neuralcore_embedding_cache_hits_total
neuralcore_embedding_cache_misses_total
neuralcore_embedding_cache_hit_rate   # Derived metric
```

Typical production cache hit rates: **30–60%** for customer-facing chatbots, **70–90%** for internal knowledge bases with repetitive queries.

---

## 7. Dimensionality & Matryoshka Embeddings

**Matryoshka Representation Learning (MRL)** — supported by `text-embedding-3-*` and `embed-v3.*` — allows you to truncate embeddings to fewer dimensions without retraining, with only a small quality penalty.

### 7.1 Dimension vs Quality Trade-off

| Dimensions | Quality vs 3072-D | Storage per vector | Use Case |
|-----------|-------------------|--------------------|----------|
| 3072 | 100% (baseline) | 12 KB | Maximum precision |
| 1536 | ~99% | 6 KB | Default recommendation |
| 1024 | ~98% | 4 KB | Storage-constrained |
| 512 | ~96% | 2 KB | High-volume, lower precision |
| 256 | ~93% | 1 KB | ANN index compression |

### 7.2 Configuring Dimensions

```python
# Use 512-dimensional embeddings for cost/storage savings
result = client.embeddings.create(
    input="my text",
    model="text-embedding-3-large",
    dimensions=512,   # Truncate from 3072 → 512
)
```

> **Important:** All embeddings in a single Qdrant collection must have the same number of dimensions. Decide your dimension before creating a knowledge base — changing it requires rebuilding the index.

---

## 8. Fine-Tuned Embeddings

For domain-specific use cases (legal, medical, financial, code), fine-tuning a base embedding model on your domain data can improve retrieval quality by **15–40%** compared to general-purpose models.

### 8.1 Training Data Format

```jsonl
{"anchor": "What is the amortization schedule?", "positive": "Amortization refers to the process of spreading out a loan into a series of fixed payments over time.", "negative": "Inflation is the rate at which the general level of prices for goods rises."}
{"anchor": "EBITDA definition", "positive": "EBITDA stands for Earnings Before Interest, Taxes, Depreciation, and Amortization.", "negative": "TCP/IP is a networking protocol stack."}
```

Minimum recommended: **1,000 pairs**. Optimal: **10,000–100,000 pairs**.

### 8.2 Fine-Tuning via API

```http
POST /api/v1/embeddings/fine-tune
{
  "base_model": "BAAI/bge-large-en-v1.5",
  "training_data_url": "s3://your-bucket/training_pairs.jsonl",
  "validation_data_url": "s3://your-bucket/validation_pairs.jsonl",
  "hyperparameters": {
    "epochs": 3,
    "batch_size": 64,
    "learning_rate": 2e-5,
    "loss_function": "MultipleNegativesRankingLoss",
    "warmup_ratio": 0.1
  },
  "output_model_name": "neuralcore-financial-embeddings-v1",
  "project_id": "proj_abc123"
}
```

**Response `202 Accepted`:**
```json
{
  "data": {
    "fine_tune_job_id": "ft_job_abc123",
    "status": "training",
    "base_model": "BAAI/bge-large-en-v1.5",
    "estimated_completion_minutes": 45
  }
}
```

### 8.3 Using a Fine-Tuned Model

```json
{
  "embedding": {
    "provider": "custom",
    "model": "neuralcore-financial-embeddings-v1",
    "dimensions": 1024
  }
}
```

---

## 9. Embedding Storage & Indexing

### 9.1 Qdrant (Default)

NeuralCore uses Qdrant as the primary vector store. Each knowledge base maps to one Qdrant collection.

**Index configuration:**

```python
# HNSW index parameters (set at collection creation)
{
    "hnsw_config": {
        "m": 16,               # Neighbors per node (higher = better quality, more RAM)
        "ef_construction": 200, # Build-time quality (higher = slower build, better index)
        "full_scan_threshold": 10000  # Use exact search for small collections
    },
    "quantization_config": {
        "scalar": {
            "type": "int8",    # 4x storage reduction, ~1% quality loss
            "quantile": 0.99,
            "always_ram": True
        }
    }
}
```

**Collection size planning:**

| Vectors | Dimensions | Storage (float32) | Storage (int8 quantized) | RAM needed |
|---------|-----------|-------------------|--------------------------|------------|
| 1M | 1536 | 6 GB | 1.5 GB | 3 GB |
| 10M | 1536 | 60 GB | 15 GB | 20 GB |
| 100M | 1536 | 600 GB | 150 GB | 80 GB |
| 1M | 3072 | 12 GB | 3 GB | 6 GB |

### 9.2 pgvector (PostgreSQL)

For deployments that want to minimize infrastructure, NeuralCore supports pgvector for storing embeddings directly in PostgreSQL alongside metadata.

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Example chunk table with embedded vector
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    knowledge_base_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER,
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index (faster inserts, lower memory)
CREATE INDEX ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- HNSW index (faster queries, higher memory)
CREATE INDEX ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 10. Similarity & Distance Metrics

NeuralCore supports three distance metrics. Choose at collection creation time — cannot be changed without rebuilding the index.

| Metric | Formula | Range | Notes |
|--------|---------|-------|-------|
| **Cosine** (default) | `1 - (a·b)/(|a||b|)` | [0, 2] | Best for text embeddings; direction only |
| **Dot Product** | `-(a·b)` | (-∞, +∞) | Faster than cosine; use if embeddings are L2-normalized |
| **Euclidean (L2)** | `√Σ(aᵢ-bᵢ)²` | [0, +∞) | Good for image/audio embeddings |

> **Best practice:** Always L2-normalize your embeddings before storage when using dot product — it becomes equivalent to cosine similarity at 3x the query speed.

NeuralCore normalizes all embeddings by default. Override with:

```yaml
embedding:
  normalize: false   # Disable if your model already normalizes
```

---

## 11. Multilingual Embeddings

### 11.1 Language Detection

NeuralCore automatically detects the input language and routes to the appropriate embedding model:

```yaml
multilingual:
  auto_detect: true
  detection_threshold: 0.85      # Confidence threshold for language detection
  fallback_language: "en"
  language_model_map:
    en: "text-embedding-3-large"
    zh: "BAAI/bge-m3"
    ja: "BAAI/bge-m3"
    de: "embed-multilingual-v3.0"
    fr: "embed-multilingual-v3.0"
    es: "embed-multilingual-v3.0"
    default: "embed-multilingual-v3.0"
```

### 11.2 Cross-Lingual Retrieval

BAAI/bge-m3 and Cohere embed-multilingual-v3.0 support **cross-lingual retrieval** — query in English, retrieve French documents (and vice versa). Enable it:

```json
{
  "retrieval": {
    "cross_lingual": true,
    "query_language": "en",
    "document_languages": ["fr", "de", "es", "en"]
  }
}
```

---

## 12. Cost & Performance Reference

### 12.1 Cost Comparison

| Provider + Model | Cost / 1M tokens | Quality (MTEB) | Latency (p50) |
|-----------------|------------------|----------------|--------------|
| OpenAI text-embedding-3-large | $0.13 | 64.6 | 45ms |
| OpenAI text-embedding-3-small | $0.02 | 62.3 | 38ms |
| Cohere embed-english-v3.0 | $0.10 | 64.5 | 55ms |
| Cohere embed-multilingual-v3.0 | $0.10 | 62.9 | 60ms |
| Local BAAI/bge-large-en-v1.5 | ~$0.001 (GPU cost) | 63.6 | 12ms (GPU) |
| Local all-MiniLM-L6-v2 | ~$0.0001 | 56.3 | 3ms (GPU) |

### 12.2 Cost Calculator

Embedding cost for a knowledge base:

```
Total Cost = (Total Tokens / 1,000,000) × Price per 1M tokens

Example: 10M token knowledge base with text-embedding-3-large
= (10,000,000 / 1,000,000) × $0.13
= $1.30 (one-time indexing cost)

Ongoing query cost (1,000 queries/day, avg 20 tokens each):
= (1,000 × 20 × 30 / 1,000,000) × $0.13
= $0.078/month
```

---

## 13. Configuration Reference

```yaml
# config/embeddings.yaml
default_provider: openai
default_model: text-embedding-3-large
default_dimensions: 1536

providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    organization: ${OPENAI_ORG}
    timeout_seconds: 30
    max_retries: 3

  cohere:
    api_key: ${COHERE_API_KEY}
    timeout_seconds: 30

  local:
    type: sentence_transformers
    model_path: /models/bge-large-en-v1.5
    device: cuda
    batch_size: 128
    normalize_embeddings: true

preprocessing:
  max_tokens: 8000
  truncation_strategy: end     # "start", "end", "middle"
  clean_whitespace: true
  lowercase: false
  strip_html: true
  remove_urls: false

postprocessing:
  normalize: true              # L2 normalization
  dtype: float32               # "float32", "float16", "int8"

batching:
  enabled: true
  max_batch_size: 100
  max_wait_ms: 50

cache:
  enabled: true
  backend: redis
  ttl_seconds: 86400           # 24 hours
  similarity_threshold: 0.99   # For semantic deduplication
  max_size_mb: 2048
```

---

## 14. Troubleshooting

### Embeddings Are Slow

```bash
# Check provider latency
curl -w "@curl-format.txt" -X POST \
  https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"input": "test", "model": "text-embedding-3-small"}'

# Enable request profiling
LOG_LEVEL=debug docker compose restart api
# Look for "embedding_latency_ms" in logs
```

**Common causes:**
- Large input text — truncate to 512 tokens for queries, 512 for document chunks
- No batching — ensure `batching.enabled: true`
- Local model not on GPU — verify `device: cuda` and GPU availability

### Low Retrieval Quality

Run the retrieval debugger:

```http
POST /api/v1/knowledge-bases/{kb_id}/retrieve/debug
{
  "query": "your test query",
  "strategy": "hybrid",
  "top_k": 20,
  "debug": true
}
```

Check:
- `similarity_threshold` — lower it to retrieve more candidates
- `chunking.chunk_size` — too large loses precision, too small loses context
- Consider switching to a higher-quality embedding model
- Verify the model dimension matches the collection dimension

### Dimension Mismatch Error

```
Error: Vector dimension 1536 does not match collection dimension 3072
```

This means you're trying to insert a 1536-D vector into a collection built with 3072-D embeddings. You must use the same model/dimensions as when the collection was created. To migrate:

```bash
# Rebuild the knowledge base index with the new model
POST /api/v1/knowledge-bases/{kb_id}/reindex
{ "embedding_model": "text-embedding-3-large", "dimensions": 1536 }
```

This will re-embed all documents (incurs API cost) and rebuild the index.

---

*For embedding model recommendations for your specific use case, contact the NeuralCore ML team at [ml@neuralcore.ai](mailto:ml@neuralcore.ai).*

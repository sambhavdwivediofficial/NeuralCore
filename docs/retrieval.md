# Retrieval

NeuralCore's retrieval system is the core engine that powers all knowledge base search, RAG pipelines, and agent grounding. It combines dense vector search, sparse keyword search, metadata filtering, cross-encoder reranking, and contextual compression into a unified, configurable pipeline that consistently delivers precise, relevant results.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Retrieval Architecture](#2-retrieval-architecture)
3. [Retrieval Strategies](#3-retrieval-strategies)
4. [Hybrid Retrieval](#4-hybrid-retrieval)
5. [Reranking](#5-reranking)
6. [Metadata Filtering](#6-metadata-filtering)
7. [Contextual Compression](#7-contextual-compression)
8. [Query Preprocessing](#8-query-preprocessing)
9. [Multi-Knowledge-Base Retrieval](#9-multi-knowledge-base-retrieval)
10. [Retrieval API](#10-retrieval-api)
11. [Retrieval Debugger](#11-retrieval-debugger)
12. [Evaluation & Quality Metrics](#12-evaluation--quality-metrics)
13. [Configuration Reference](#13-configuration-reference)
14. [Performance Tuning](#14-performance-tuning)

---

## 1. Overview

Retrieval in NeuralCore is the process of finding the most relevant document chunks from a knowledge base given a query. It operates at sub-100ms latency for most workloads and is designed to be used both programmatically (via API) and automatically (inside agent runs).

### The Retrieval Problem

```
User Query: "What is the cancellation policy for enterprise subscriptions?"
                                │
                                ▼
                    10 million document chunks
                          in Qdrant
                                │
                         How do we find the
                         3-5 chunks that actually
                         answer this question?
                                │
                                ▼
             NeuralCore Retrieval Pipeline
                    (this document)
```

### What Good Retrieval Looks Like

| Metric | Target | Notes |
|--------|--------|-------|
| Precision@5 | > 0.85 | 4+ of top 5 results are genuinely relevant |
| Recall@20 | > 0.90 | 90%+ of all relevant docs appear in top 20 |
| Latency P50 | < 80ms | For hybrid + reranking on 1M vectors |
| Latency P99 | < 500ms | Including reranking |
| Relevance (human eval) | > 4.0/5.0 | Expert annotation |

---

## 2. Retrieval Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Retrieval Pipeline                              │
│                                                                      │
│  User / Agent Query                                                  │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────────────┐                                             │
│  │  Query Preprocessor │                                             │
│  │  - expand           │                                             │
│  │  - decompose        │                                             │
│  │  - detect intent    │                                             │
│  │  - translate        │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│    ┌────────┴────────┐                                               │
│    │                 │                                               │
│    ▼                 ▼                                               │
│  Dense           Sparse                                              │
│  Search          Search                                              │
│  (Qdrant)        (BM25)                                              │
│  top_k×2         top_k×2                                            │
│    │                 │                                               │
│    └────────┬────────┘                                               │
│             │                                                        │
│             ▼                                                        │
│  ┌─────────────────────┐                                             │
│  │  Reciprocal Rank    │                                             │
│  │  Fusion (RRF)       │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│             ▼                                                        │
│  ┌─────────────────────┐                                             │
│  │  Metadata Filter    │                                             │
│  │  (pre or post)      │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│             ▼                                                        │
│  ┌─────────────────────┐                                             │
│  │  Cross-Encoder      │                                             │
│  │  Reranker           │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│             ▼                                                        │
│  ┌─────────────────────┐                                             │
│  │  Contextual         │                                             │
│  │  Compression        │                                             │
│  └──────────┬──────────┘                                             │
│             │                                                        │
│             ▼                                                        │
│       top_k results                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Retrieval Strategies

### 3.1 Semantic (Dense Vector) Search

Embeds the query and finds the nearest vectors in Qdrant using cosine similarity.

**Strengths:** Understands synonyms, paraphrases, and semantic equivalence.
**Weaknesses:** Can miss exact keyword matches; struggles with rare technical terms.

```json
{
  "strategy": "semantic",
  "top_k": 10,
  "min_similarity_score": 0.70
}
```

**How it works:**
```
Query: "policy for cancelling subscription"
         │
         ▼
Embed → [0.021, -0.043, 0.091, ...]
         │
         ▼
Qdrant cosine search over 10M vectors
         │
         ▼
Results: chunks similar to the query vector
  - "Subscription termination: accounts may be cancelled..."  (0.91)
  - "To discontinue your plan, navigate to..."               (0.88)
  - "Refund policy for cancelled memberships..."             (0.84)
```

### 3.2 Keyword (Sparse / BM25) Search

Classic information retrieval using term frequency and inverse document frequency.

**Strengths:** Excellent for exact matches, product names, codes, jargon.
**Weaknesses:** No semantic understanding; "cancel" ≠ "terminate".

```json
{
  "strategy": "keyword",
  "top_k": 10,
  "bm25": {
    "k1": 1.5,
    "b": 0.75
  }
}
```

### 3.3 Hybrid Search

Combines dense and sparse results using Reciprocal Rank Fusion (RRF). **This is the production default** and consistently outperforms either approach alone.

```json
{
  "strategy": "hybrid",
  "top_k": 10,
  "hybrid": {
    "alpha": 0.7,
    "fusion": "rrf",
    "rrf_k": 60
  }
}
```

`alpha` controls the weight balance:
- `alpha: 1.0` → pure semantic
- `alpha: 0.0` → pure keyword
- `alpha: 0.7` → 70% semantic + 30% keyword (recommended)

### 3.4 Full Pipeline (Hybrid + Reranking)

```json
{
  "strategy": "hybrid",
  "top_k": 5,
  "pre_rerank_top_k": 20,
  "reranking": {
    "enabled": true,
    "model": "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "top_k_after_rerank": 5
  }
}
```

---

## 4. Hybrid Retrieval

### 4.1 Reciprocal Rank Fusion (RRF)

RRF merges ranked lists from multiple retrieval systems without requiring score normalization:

```
Dense results (top 20):     Sparse results (top 20):
  1. chunk_A (0.92)           1. chunk_B (BM25: 14.2)
  2. chunk_B (0.89)           2. chunk_C (BM25: 11.7)
  3. chunk_C (0.85)           3. chunk_A (BM25: 10.1)
  ...                         ...

RRF Score = Σ 1/(k + rank_i)   where k=60 (default)

chunk_A: 1/(60+1) + 1/(60+3) = 0.01639 + 0.01587 = 0.03226
chunk_B: 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252  ← winner
chunk_C: 1/(60+3) + 1/(60+2) = 0.01587 + 0.01613 = 0.03200

Final order: B, A, C
```

### 4.2 Weighted Score Fusion

Alternative to RRF — combines normalized scores directly:

```json
{
  "hybrid": {
    "fusion": "weighted",
    "dense_weight": 0.7,
    "sparse_weight": 0.3,
    "score_normalization": "min_max"
  }
}
```

### 4.3 Qdrant Sparse Vectors

NeuralCore uses Qdrant's native sparse vector support for BM25 storage, avoiding the need for a separate Elasticsearch cluster:

```python
# Internal: indexing sparse BM25 vector alongside dense vector
{
    "id": "chunk_abc001",
    "vector": {
        "dense": [0.021, -0.043, ...],   # 1536-D dense
        "sparse": {                       # BM25 sparse
            "indices": [1204, 3891, 7823],
            "values": [0.821, 0.634, 0.412]
        }
    },
    "payload": { "...metadata..." }
}
```

---

## 5. Reranking

Reranking is a second-pass scoring step that uses a more powerful (but slower) cross-encoder model to re-score the candidates retrieved in the first pass.

### 5.1 Why Rerank?

```
First pass (bi-encoder, fast): retrieves top 20 candidates in ~30ms
  ↓ Quality: good (each text encoded independently)

Second pass (cross-encoder, slow): reranks top 20 in ~150ms
  ↓ Quality: excellent (query and document encoded jointly, capturing interaction)

Without reranking:  Precision@5 ≈ 0.72
With reranking:     Precision@5 ≈ 0.89  (+24%)
Latency cost:       +120–200ms
```

### 5.2 Available Reranker Models

| Model | Quality | Latency | Use Case |
|-------|---------|---------|----------|
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | Good | 120ms | Default, balanced |
| `cross-encoder/ms-marco-electra-base` | Better | 200ms | Higher precision |
| `BAAI/bge-reranker-large` | Best open-source | 250ms | Maximum precision |
| `cohere-rerank-3` | Excellent | 300ms (API) | Multilingual |
| `jina-reranker-v2-base-multilingual` | Very good | 180ms | Multilingual |

### 5.3 Configuration

```json
{
  "reranking": {
    "enabled": true,
    "model": "BAAI/bge-reranker-large",
    "top_k_after_rerank": 5,
    "min_rerank_score": 0.5,
    "batch_size": 32,
    "device": "cuda"
  }
}
```

### 5.4 Cohere Rerank API

```json
{
  "reranking": {
    "enabled": true,
    "provider": "cohere",
    "model": "rerank-english-v3.0",
    "top_k_after_rerank": 5
  }
}
```

---

## 6. Metadata Filtering

Filter retrieval results based on document metadata. Filters can be applied before retrieval (pre-filter, reduces search space) or after (post-filter, on already-retrieved results).

### 6.1 Simple Filters

```json
{
  "filters": {
    "metadata": {
      "document_type": "policy",
      "language": "en",
      "product_version": "4.x"
    }
  }
}
```

### 6.2 Advanced Filters

```json
{
  "filters": {
    "metadata": {
      "document_type": {"in": ["policy", "faq", "guide"]},
      "contract_value_usd": {"gte": 100000, "lte": 1000000},
      "effective_date": {"gte": "2025-01-01"},
      "department": {"nin": ["deprecated", "archived"]},
      "language": {"in": ["en", "fr"]},
      "confidentiality": {"not": "restricted"}
    },
    "text": {
      "contains": "enterprise",
      "not_contains": "trial"
    }
  }
}
```

### 6.3 Filter Operators

| Operator | Type | Example |
|----------|------|---------|
| `eq` (default) | Equality | `{"status": "active"}` |
| `ne` / `not` | Not equal | `{"status": {"ne": "deleted"}}` |
| `in` | In set | `{"type": {"in": ["a","b"]}}` |
| `nin` | Not in set | `{"type": {"nin": ["x","y"]}}` |
| `gt` / `gte` | Greater than | `{"score": {"gte": 0.8}}` |
| `lt` / `lte` | Less than | `{"date": {"lte": "2026-01-01"}}` |
| `exists` | Field exists | `{"category": {"exists": true}}` |
| `regex` | Regex match | `{"title": {"regex": "^API.*"}}` |

### 6.4 Pre-filter vs Post-filter

```json
{
  "filter_mode": "pre"     // Apply filter before vector search (fast, limits recall)
}
```
```json
{
  "filter_mode": "post"    // Apply filter after vector search (slower, full recall)
}
```

**Rule of thumb:** Use `pre` when your filter is highly selective (< 10% of docs match). Use `post` when filter is loose (> 50% match).

---

## 7. Contextual Compression

After retrieval, chunks may contain irrelevant surrounding text. Contextual compression extracts only the sentences most relevant to the query:

```
Query: "What is the cancellation fee?"

Retrieved chunk (512 tokens):
"Our subscription plans are available monthly and annually. Annual plans 
offer a 20% discount over monthly pricing. [... 200 tokens of pricing info ...]
Early cancellation of annual plans incurs a fee of 20% of the remaining 
contract value. Monthly plans can be cancelled at any time with no fee.
[... 100 tokens about renewal ...]"

After contextual compression (40 tokens):
"Early cancellation of annual plans incurs a fee of 20% of the remaining 
contract value. Monthly plans can be cancelled at any time with no fee."
```

### 7.1 Configuration

```json
{
  "contextual_compression": {
    "enabled": true,
    "method": "llm",
    "model": "gpt-4o-mini",
    "max_compressed_tokens": 200,
    "min_relevance_score": 0.6,
    "preserve_citations": true
  }
}
```

**Methods:**

| Method | Quality | Speed | Cost |
|--------|---------|-------|------|
| `llm` | Excellent | Slow | High |
| `sentence_score` | Good | Fast | None |
| `extractive` | Fair | Fastest | None |

### 7.2 Sentence-Level Compression

Faster alternative using embedding similarity to score individual sentences:

```json
{
  "contextual_compression": {
    "enabled": true,
    "method": "sentence_score",
    "top_n_sentences": 3,
    "min_sentence_score": 0.75
  }
}
```

---

## 8. Query Preprocessing

### 8.1 Query Expansion

Automatically expands the query with synonyms and related terms to improve recall:

```
Original: "ML ops"
Expanded: "MLOps machine learning operations model deployment model monitoring"
```

```json
{
  "query_preprocessing": {
    "expansion": {
      "enabled": true,
      "method": "llm",
      "model": "gpt-4o-mini",
      "max_expansion_terms": 5
    }
  }
}
```

### 8.2 Query Decomposition (Multi-Hop)

For complex questions that require retrieving from multiple sub-topics:

```
Complex query: "Compare the cancellation policies for monthly and annual plans, 
                and explain when refunds are issued"

Decomposed into:
  1. "cancellation policy monthly plans"
  2. "cancellation policy annual plans"  
  3. "refund policy when issued"

Each sub-query retrieves independently → results merged and deduplicated
```

```json
{
  "query_preprocessing": {
    "decomposition": {
      "enabled": true,
      "model": "gpt-4o-mini",
      "max_sub_queries": 4,
      "merge_strategy": "union_dedup"
    }
  }
}
```

### 8.3 Hypothetical Document Embedding (HyDE)

Instead of embedding the query directly, generate a hypothetical answer and embed that — it tends to be closer to real answer embeddings in vector space:

```
Query: "What is the refund timeline?"

HyDE generates: "Refunds are typically processed within 5-7 business days 
after the cancellation is confirmed. For credit card payments..."

Embed the hypothetical answer → retrieve using that embedding
```

```json
{
  "query_preprocessing": {
    "hyde": {
      "enabled": true,
      "model": "gpt-4o-mini",
      "num_hypothetical_docs": 1
    }
  }
}
```

HyDE improves recall by 10–20% for factual Q&A tasks.

### 8.4 Query Translation

For multilingual knowledge bases, translate the query before retrieval:

```json
{
  "query_preprocessing": {
    "translation": {
      "enabled": true,
      "target_language": "en",
      "model": "gpt-4o-mini",
      "detect_source_language": true
    }
  }
}
```

---

## 9. Multi-Knowledge-Base Retrieval

Retrieve across multiple knowledge bases simultaneously:

```http
POST /api/v1/retrieve/multi
{
  "query": "cancellation policy",
  "knowledge_bases": [
    {
      "id": "kb_policies",
      "weight": 1.0,
      "top_k": 5
    },
    {
      "id": "kb_support_articles",
      "weight": 0.8,
      "top_k": 5
    },
    {
      "id": "kb_legal_docs",
      "weight": 0.6,
      "top_k": 3,
      "filters": {"metadata": {"doc_type": "terms_of_service"}}
    }
  ],
  "merge_strategy": "weighted_rrf",
  "final_top_k": 10,
  "reranking": {"enabled": true}
}
```

### Merge Strategies

| Strategy | Description |
|----------|-------------|
| `union` | All results pooled, deduplicated, sorted by score |
| `interleave` | Round-robin from each KB |
| `weighted_rrf` | RRF with per-KB weights |
| `cascade` | Search KB2 only if KB1 returns < threshold results |

---

## 10. Retrieval API

### 10.1 Basic Retrieval

```http
POST /api/v1/knowledge-bases/{kb_id}/retrieve
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "What is the enterprise cancellation policy?",
  "strategy": "hybrid",
  "top_k": 5,
  "min_similarity_score": 0.65,
  "filters": {
    "metadata": {
      "document_type": {"in": ["policy", "contract"]}
    }
  },
  "reranking": {
    "enabled": true,
    "model": "BAAI/bge-reranker-large",
    "top_k_after_rerank": 5
  },
  "include_metadata": true,
  "include_embeddings": false
}
```

**Response:**
```json
{
  "data": {
    "query": "What is the enterprise cancellation policy?",
    "strategy_used": "hybrid",
    "results": [
      {
        "rank": 1,
        "chunk_id": "chunk_abc001",
        "document_id": "doc_policy_001",
        "document_title": "Enterprise Subscription Terms",
        "text": "Enterprise subscriptions may be cancelled with 30 days written notice. Annual contracts cancelled before term end incur a 20% early termination fee...",
        "similarity_score": 0.921,
        "bm25_score": 14.2,
        "hybrid_score": 0.887,
        "rerank_score": 0.934,
        "final_rank": 1,
        "metadata": {
          "document_type": "contract",
          "page_number": 7,
          "section": "Cancellation and Termination",
          "effective_date": "2025-01-01"
        }
      }
    ],
    "total_candidates_retrieved": 40,
    "total_after_filter": 22,
    "total_after_rerank": 5,
    "retrieval_latency_ms": 67,
    "reranking_latency_ms": 143,
    "total_latency_ms": 210
  }
}
```

### 10.2 Python SDK

```python
from neuralcore import NeuralCoreClient

client = NeuralCoreClient(api_key="nck_...")

results = client.knowledge_bases.retrieve(
    kb_id="kb_xyz789",
    query="enterprise cancellation policy",
    strategy="hybrid",
    top_k=5,
    filters={"document_type": {"in": ["policy", "contract"]}},
    reranking=True,
)

for result in results:
    print(f"[{result.rank}] {result.document_title} (score: {result.final_score:.3f})")
    print(f"  {result.text[:200]}...")
    print()
```

### 10.3 Async Retrieval

```python
import asyncio
from neuralcore.async_client import AsyncNeuralCoreClient

async def retrieve_parallel():
    async with AsyncNeuralCoreClient(api_key="nck_...") as client:
        # Run 3 retrievals in parallel
        results = await asyncio.gather(
            client.knowledge_bases.retrieve(kb_id="kb_1", query="cancellation"),
            client.knowledge_bases.retrieve(kb_id="kb_2", query="refund policy"),
            client.knowledge_bases.retrieve(kb_id="kb_3", query="termination fee"),
        )
    return results
```

---

## 11. Retrieval Debugger

The retrieval debugger provides full visibility into every stage of the pipeline — essential for tuning and diagnosing low-quality results.

### 11.1 Debug Request

```http
POST /api/v1/knowledge-bases/{kb_id}/retrieve/debug
{
  "query": "cancellation fee enterprise",
  "strategy": "hybrid",
  "top_k": 5,
  "debug": {
    "show_all_candidates": true,
    "show_scores_breakdown": true,
    "show_filter_details": true,
    "show_query_preprocessing": true
  }
}
```

### 11.2 Debug Response

```json
{
  "data": {
    "query_preprocessing": {
      "original": "cancellation fee enterprise",
      "expanded": "cancellation fee enterprise termination early exit penalty",
      "detected_language": "en",
      "intent": "factual_lookup"
    },
    "dense_results": {
      "top_20": [
        {"chunk_id": "chunk_abc001", "score": 0.921, "rank": 1},
        {"chunk_id": "chunk_xyz002", "score": 0.887, "rank": 2}
      ],
      "latency_ms": 34
    },
    "sparse_results": {
      "top_20": [
        {"chunk_id": "chunk_abc001", "bm25_score": 14.2, "rank": 1},
        {"chunk_id": "chunk_def003", "bm25_score": 11.8, "rank": 2}
      ],
      "latency_ms": 12
    },
    "fusion": {
      "method": "rrf",
      "merged_candidates": 35,
      "after_dedup": 28
    },
    "filter_result": {
      "before": 28,
      "after": 14,
      "filter_applied": {"document_type": {"in": ["policy"]}}
    },
    "reranking": {
      "input_candidates": 14,
      "output_top_k": 5,
      "model": "BAAI/bge-reranker-large",
      "scores": [
        {"chunk_id": "chunk_abc001", "before_rerank_rank": 1, "after_rerank_rank": 1, "rerank_score": 0.934},
        {"chunk_id": "chunk_xyz002", "before_rerank_rank": 2, "after_rerank_rank": 3, "rerank_score": 0.721}
      ],
      "latency_ms": 143
    },
    "final_results": []
  }
}
```

### 11.3 Common Debug Findings

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Good dense, bad sparse results | Missing keywords in docs | Lower `alpha` (more sparse weight) |
| Good sparse, bad dense results | Domain-specific jargon | Fine-tune embedding model |
| Top result is wrong but #3 is correct | Reranker needs tuning | Try a stronger reranker |
| All results are wrong | Wrong KB, wrong filters | Check kb_id and filter logic |
| Results from wrong document type | Filter not applied | Add `document_type` filter |
| Latency > 500ms | Too many candidates | Reduce `pre_rerank_top_k` |

---

## 12. Evaluation & Quality Metrics

### 12.1 Automated Evaluation

Run the retrieval evaluator against a labeled test set:

```http
POST /api/v1/knowledge-bases/{kb_id}/evaluate/retrieval
{
  "test_set": [
    {
      "query": "What is the cancellation policy?",
      "relevant_chunk_ids": ["chunk_abc001", "chunk_abc002"]
    },
    {
      "query": "How long do refunds take?",
      "relevant_chunk_ids": ["chunk_xyz005"]
    }
  ],
  "retrieval_config": {
    "strategy": "hybrid",
    "top_k": 5,
    "reranking": {"enabled": true}
  }
}
```

**Response:**
```json
{
  "data": {
    "num_queries": 50,
    "metrics": {
      "precision_at_1": 0.82,
      "precision_at_3": 0.79,
      "precision_at_5": 0.76,
      "recall_at_5": 0.88,
      "recall_at_10": 0.94,
      "ndcg_at_5": 0.83,
      "mrr": 0.87,
      "hit_rate_at_5": 0.92
    },
    "latency": {
      "p50_ms": 78,
      "p95_ms": 312,
      "p99_ms": 487
    }
  }
}
```

### 12.2 Key Metrics Explained

| Metric | What it Measures | Target |
|--------|-----------------|--------|
| **Precision@K** | % of top-K results that are relevant | > 0.80 |
| **Recall@K** | % of all relevant docs found in top-K | > 0.85 |
| **NDCG@K** | Ranks higher-relevance docs first | > 0.80 |
| **MRR** | How early the first relevant doc appears | > 0.85 |
| **Hit Rate@K** | % of queries with at least one relevant result in top-K | > 0.95 |

### 12.3 A/B Testing Retrieval Configs

```http
POST /api/v1/knowledge-bases/{kb_id}/evaluate/ab-test
{
  "test_set_url": "s3://your-bucket/eval/queries.jsonl",
  "config_a": {
    "name": "Baseline",
    "strategy": "semantic",
    "top_k": 5
  },
  "config_b": {
    "name": "Hybrid + Rerank",
    "strategy": "hybrid",
    "top_k": 5,
    "reranking": {"enabled": true}
  }
}
```

---

## 13. Configuration Reference

```yaml
# config/retrieval.yaml

defaults:
  strategy: hybrid
  top_k: 5
  pre_rerank_top_k: 20
  min_similarity_score: 0.65
  include_metadata: true
  include_embeddings: false

hybrid:
  alpha: 0.7
  fusion: rrf
  rrf_k: 60

reranking:
  enabled: true
  model: cross-encoder/ms-marco-MiniLM-L-12-v2
  provider: local               # "local", "cohere", "jina"
  device: cuda
  batch_size: 32
  top_k_after_rerank: 5
  min_rerank_score: 0.3

contextual_compression:
  enabled: false
  method: sentence_score
  top_n_sentences: 5
  min_sentence_score: 0.7

query_preprocessing:
  expansion:
    enabled: false
  decomposition:
    enabled: false
  hyde:
    enabled: false
  translation:
    enabled: false
    auto_detect: true
    target_language: en

caching:
  semantic_cache:
    enabled: true
    similarity_threshold: 0.97
    ttl_seconds: 3600
  exact_cache:
    enabled: true
    ttl_seconds: 300

monitoring:
  trace_every_request: true
  slow_query_threshold_ms: 500
  log_scores: false           # Enable for debugging; verbose in production
```

---

## 14. Performance Tuning

### 14.1 Latency Optimization

| Technique | Latency Reduction | Quality Impact |
|-----------|------------------|---------------|
| Reduce `pre_rerank_top_k` from 40 to 20 | -30% | Minimal |
| Use `MiniLM` reranker instead of `bge-large` | -40% | Small |
| Enable semantic caching | -90% on cache hits | None |
| Use GPU for reranking | -60% | None |
| Disable reranking entirely | -50% | Moderate |
| Use pgvector instead of Qdrant | +10% (slower) | None |
| Use HNSW `ef` = 64 instead of 128 | -20% | Small |

### 14.2 Quality Optimization

| Technique | Quality Improvement | Latency Cost |
|-----------|--------------------|----|
| Enable reranking | +20-25% Precision@5 | +150ms |
| Switch to hybrid from semantic | +10-15% | +20ms |
| Use `bge-reranker-large` vs `MiniLM` | +5% | +80ms |
| Enable HyDE | +10-20% Recall | +200ms |
| Enable query expansion | +8-12% Recall | +150ms |
| Use `text-embedding-3-large` vs `small` | +3-5% | +10ms |
| Fine-tune embedding model | +15-40% | None |

### 14.3 Large-Scale Retrieval (>100M vectors)

```yaml
# Qdrant optimization for large collections
qdrant:
  hnsw_config:
    m: 16
    ef_construction: 100         # Lower than default for faster indexing
    ef: 64                       # Lower ef for faster queries at slight quality cost
  quantization:
    scalar:
      type: int8
      always_ram: false          # Let Qdrant manage RAM/disk tiering
  optimizer_config:
    indexing_threshold: 50000    # Don't index until 50K vectors (batch mode)
    memmap_threshold: 100000     # Use memory-mapped storage for large segments
```

### 14.4 Retrieval Cost Optimization

For high-query-volume deployments:

- **Semantic cache** — 30–60% of queries are near-duplicates in production; cache hit = $0
- **Use `text-embedding-3-small`** for query embedding (6× cheaper, ~97% quality vs large)
- **Only embed queries, not documents** — documents are already embedded at ingestion time
- **Batch query embedding** — for batch evaluation / offline analytics, use batch embedding API

---

*For retrieval quality issues, custom reranker integration, or evaluation dataset creation, see [CONTRIBUTING.md](CONTRIBUTING.md) or open a GitHub issue tagged `area:retrieval`.*

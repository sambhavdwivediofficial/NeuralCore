# Memory

NeuralCore's memory system gives agents the ability to remember, recall, and reason over information that persists beyond a single conversation turn. This document covers all four memory layers, their storage backends, injection mechanics, management APIs, and operational best practices.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Memory Architecture](#2-memory-architecture)
3. [Working Memory](#3-working-memory)
4. [Episodic Memory](#4-episodic-memory)
5. [Semantic Memory](#5-semantic-memory)
6. [Long-Term Structured Memory](#6-long-term-structured-memory)
7. [Memory Injection](#7-memory-injection)
8. [Memory Extraction & Auto-Learning](#8-memory-extraction--auto-learning)
9. [Memory Management API](#9-memory-management-api)
10. [Privacy & Data Isolation](#10-privacy--data-isolation)
11. [Configuration Reference](#11-configuration-reference)
12. [Performance & Scaling](#12-performance--scaling)

---

## 1. Overview

Without memory, every agent conversation starts from scratch. With NeuralCore's four-layer memory system, agents can:

- **Remember** what a specific user told them three conversations ago
- **Learn** user preferences over time without explicit instruction
- **Recall** facts relevant to the current conversation from thousands of past interactions
- **Summarize** long conversations to avoid context window overflow
- **Isolate** memory strictly per user, per project, per tenant

### Memory vs Knowledge Base

| | Memory | Knowledge Base |
|--|--------|---------------|
| **Content** | User-specific, conversational | Document corpus, static knowledge |
| **Who writes it** | Agent (auto-extracted from conversations) | Humans (via ingestion pipeline) |
| **Who reads it** | The same agent, for the same user | Any agent in the project |
| **Scope** | Per-user, per-agent | Per-project |
| **TTL** | Configurable (24h → permanent) | Permanent (until deleted) |
| **Storage** | Redis + PostgreSQL + Qdrant | Qdrant + PostgreSQL |

---

## 2. Memory Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    NeuralCore Memory System                          │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   Working Memory (RAM)                          │ │
│  │   Active conversation messages for this run only               │ │
│  │   Max: 50 messages / 8,000 tokens (configurable)               │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   Episodic Memory (Redis)                       │ │
│  │   Recent sessions, raw turn-by-turn history                    │ │
│  │   Scope: per user, per agent                                   │ │
│  │   TTL: 24h–30d (configurable)                                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   Semantic Memory (Qdrant)                      │ │
│  │   Embedded summaries of past interactions, retrieved by         │ │
│  │   similarity to current query                                  │ │
│  │   Scope: per user, per agent                                   │ │
│  │   TTL: permanent (or configurable)                             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              Long-Term Structured Memory (PostgreSQL)           │ │
│  │   Extracted facts, preferences, entities, and key decisions    │ │
│  │   Scope: per user, per agent                                   │ │
│  │   TTL: permanent                                               │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Working Memory

Working memory is the active conversation window — the messages that are directly in context for the current agent run. It is ephemeral and exists only for the duration of a single run.

### 3.1 What It Contains

```
System Prompt
    +
Injected Memory (from layers below)
    +
Current Conversation History
    = Working Memory (must fit in model's context window)
```

### 3.2 Window Management

When the conversation grows too large to fit in the context window, NeuralCore automatically applies the configured overflow strategy:

| Strategy | Behavior | Best For |
|----------|----------|----------|
| `sliding_window` | Drop oldest messages first | Continuous chat assistants |
| `summarize` | Replace oldest N messages with an LLM summary | Long task-oriented sessions |
| `trim_to_budget` | Drop messages least likely to be relevant | Balanced quality/cost |
| `raise_error` | Fail the run with `CONTEXT_LENGTH_EXCEEDED` | Strict pipelines |

```json
{
  "memory": {
    "working_memory": {
      "max_messages": 50,
      "max_tokens": 8000,
      "overflow_strategy": "summarize",
      "summarization_model": "gpt-4o-mini",
      "summarization_target_tokens": 500
    }
  }
}
```

### 3.3 Token Budgeting

NeuralCore pre-calculates the token budget for each run:

```
Total model context window (e.g. 128,000 tokens)
  - System prompt tokens
  - Injected memory tokens
  - Reserved for completion (max_tokens)
  ─────────────────────────────────────────
  = Available for conversation history

If history > available:
    Apply overflow_strategy
```

---

## 4. Episodic Memory

Episodic memory stores the raw, unprocessed history of past interactions for a specific user and agent. Think of it as a short-to-medium-term diary.

### 4.1 Storage

- **Backend:** Redis (hot, fast access) + PostgreSQL (persistent backup)
- **Structure:** Turn-by-turn message pairs (user + assistant), grouped by session
- **TTL:** Configurable per agent (default: 24 hours for session data)

### 4.2 What Gets Stored

Every time an agent run completes, the turn is written to episodic memory:

```json
{
  "episode_id": "ep_abc123",
  "agent_id": "agent_9f3kd82",
  "user_id": "user_456",
  "session_id": "session_user123",
  "tenant_id": "tenant_xyz",
  "timestamp": "2026-06-18T10:00:00Z",
  "turn": {
    "user": "What is the refund timeline for enterprise customers?",
    "assistant": "Enterprise refunds are processed within 3-5 business days...",
    "tool_calls": ["kb_retrieval"],
    "latency_ms": 3240,
    "tokens": 892
  },
  "session_metadata": {
    "channel": "web_chat",
    "user_plan": "enterprise"
  },
  "expires_at": "2026-06-25T10:00:00Z"
}
```

### 4.3 Session Continuity

When a user returns within the session TTL, the agent automatically loads recent episodic memory:

```python
# Provide session_id to maintain continuity across requests
result = client.agents.run(
    agent_id="agent_9f3kd82",
    input="And what about partial refunds?",
    session_id="session_user123",   # Same session = agent remembers previous turns
    user_id="user_456",
)
```

### 4.4 Configuration

```json
{
  "memory": {
    "episodic": {
      "enabled": true,
      "session_ttl_hours": 24,
      "max_turns_per_session": 100,
      "max_sessions_retained": 20,
      "include_tool_calls": false,
      "include_metadata": true,
      "inject_last_n_turns": 10
    }
  }
}
```

---

## 5. Semantic Memory

Semantic memory is the long-range recall layer. It stores embedded summaries of past interactions and retrieves the most semantically relevant ones for each new query — even if they happened months ago.

### 5.1 How It Works

```
After each session (or every N turns):
    1. Summarize the session → "User Alice asked about refund timelines 
                                for enterprise plans and learned 3-5 days"
    2. Embed the summary → [0.021, -0.043, ...]
    3. Store in Qdrant (user-scoped collection)

Before each agent run:
    1. Embed the current query
    2. Search for similar past interactions (cosine similarity)
    3. Inject top-K matches into the system prompt
```

### 5.2 Storage

- **Backend:** Qdrant (separate user-scoped collection per agent)
- **Content:** LLM-generated summaries of past sessions/episodes
- **Indexing:** Per-user, per-agent vector namespace
- **TTL:** Permanent by default; configurable decay

### 5.3 What Gets Stored

```json
{
  "memory_id": "smem_abc123",
  "agent_id": "agent_9f3kd82",
  "user_id": "user_456",
  "tenant_id": "tenant_xyz",
  "summary": "User is an enterprise customer concerned about refund processing time. Learned that enterprise refunds take 3-5 business days. Follow-up about partial refunds — learned these are handled case-by-case via support ticket.",
  "source_episodes": ["ep_abc123", "ep_def456"],
  "session_date": "2026-06-18",
  "embedding": [...],
  "metadata": {
    "topics": ["refunds", "enterprise", "support"],
    "sentiment": "neutral",
    "resolution": "resolved"
  }
}
```

### 5.4 Configuration

```json
{
  "memory": {
    "semantic": {
      "enabled": true,
      "embedding_model": "text-embedding-3-large",
      "dimensions": 1536,
      "summarize_after_turns": 10,
      "summarization_model": "gpt-4o-mini",
      "top_k_retrieve": 5,
      "similarity_threshold": 0.72,
      "max_tokens_injected": 2000,
      "decay_weight": 0.95,
      "decay_period_days": 30
    }
  }
}
```

**Decay weight:** Old memories are progressively down-ranked. A decay of `0.95` per 30 days means a memory from 90 days ago has its score multiplied by `0.95³ = 0.857` before ranking.

---

## 6. Long-Term Structured Memory

Structured memory stores explicitly extracted facts, preferences, and entities as rows in PostgreSQL — not as vectors, but as structured data that can be queried, updated, and filtered precisely.

### 6.1 Automatically Extracted Facts

After each session, an extraction model analyzes the conversation and extracts structured facts:

```
Conversation:
  User: "I'm the CTO at Acme Corp. We use the enterprise plan."
  User: "My team has 50 engineers who use the API."
  User: "We prefer Python and avoid JavaScript libraries."

Extracted facts:
  - role: "CTO"
  - company: "Acme Corp"
  - plan: "enterprise"
  - team_size: 50
  - primary_language: "Python"
  - avoided_tech: ["JavaScript libraries"]
```

### 6.2 Fact Schema

```json
{
  "fact_id": "fact_abc123",
  "agent_id": "agent_9f3kd82",
  "user_id": "user_456",
  "tenant_id": "tenant_xyz",
  "category": "user_profile",
  "key": "preferred_programming_language",
  "value": "Python",
  "confidence": 0.97,
  "source_episode_id": "ep_abc123",
  "first_observed": "2026-06-10T09:00:00Z",
  "last_confirmed": "2026-06-18T10:00:00Z",
  "confirmation_count": 3,
  "contradicted_at": null
}
```

### 6.3 Fact Categories

| Category | Examples |
|----------|---------|
| `user_profile` | name, role, company, location, plan |
| `preferences` | language, format, communication style |
| `context` | current project, team size, tech stack |
| `decisions` | past choices, resolved issues |
| `entities` | products used, vendors, colleagues |
| `goals` | what they're trying to achieve |
| `constraints` | deadlines, budget limits, restrictions |

### 6.4 Configuration

```json
{
  "memory": {
    "long_term": {
      "enabled": true,
      "auto_extract": true,
      "extraction_model": "gpt-4o-mini",
      "extract_categories": [
        "user_profile",
        "preferences",
        "context",
        "decisions"
      ],
      "min_confidence": 0.80,
      "max_facts_per_user": 500,
      "dedup_similar_facts": true,
      "contradiction_handling": "update"
    }
  }
}
```

### 6.5 Manual Fact Injection

You can directly inject facts into an agent's long-term memory without a conversation:

```python
client.agents.memory.store(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    facts=[
        {
            "category": "user_profile",
            "key": "preferred_language",
            "value": "Python",
            "confidence": 1.0
        },
        {
            "category": "context",
            "key": "primary_use_case",
            "value": "Building internal RAG pipeline for legal document review",
            "confidence": 1.0
        }
    ]
)
```

---

## 7. Memory Injection

Before every LLM call in an agent run, NeuralCore assembles and injects relevant memory into the context.

### 7.1 Injection Order

```
[System Prompt — agent persona, instructions, tools]

--- MEMORY ---
[Long-term facts: role, preferences, key context about this user]
[Semantic memory: top-K relevant past interaction summaries]
[Recent episodic: last N turns from this session]
--- END MEMORY ---

[Current conversation]
User: <current input>
```

### 7.2 Memory Budget

The total memory injected is bounded by `max_memory_tokens`. NeuralCore prioritizes:

1. Long-term structured facts (always injected if they exist)
2. Most recent episodic turns (always injected up to `inject_last_n_turns`)
3. Semantic memories (injected up to `max_tokens_injected`, ranked by relevance)

```json
{
  "memory": {
    "injection": {
      "max_total_tokens": 4000,
      "long_term_max_tokens": 500,
      "episodic_max_tokens": 1000,
      "semantic_max_tokens": 2000,
      "include_timestamps": true,
      "format": "structured"
    }
  }
}
```

### 7.3 Formatted Memory Example

What gets injected into the context:

```
--- USER MEMORY ---
Profile: CTO at Acme Corp. Enterprise plan. Team of 50 engineers.
Preferences: Prefers Python. Concise responses. Technical depth welcome.
Current focus: Building RAG pipeline for legal document review.

Recent context (last 2 sessions):
[2026-06-15] Asked about embedding models — recommended text-embedding-3-large for legal text. Chose to use it.
[2026-06-16] Debugged chunking strategy — switched from fixed to semantic chunking.

Relevant past interactions:
[2026-06-10] Discussed retrieval strategies. User opted for hybrid search with reranking.
--- END MEMORY ---
```

---

## 8. Memory Extraction & Auto-Learning

### 8.1 Session Summarization

Triggered automatically after a session ends (or after `summarize_after_turns` turns):

```python
# Internally called after session closes
summary = llm.complete(
    model="gpt-4o-mini",
    prompt=f"""
    Summarize this conversation in 2-3 sentences, focusing on:
    - What the user was trying to accomplish
    - Key information they shared about themselves
    - What was resolved or decided
    - Any important facts to remember
    
    Conversation:
    {format_conversation(turns)}
    """,
    max_tokens=200
)
```

### 8.2 Fact Extraction

```python
facts = llm.complete(
    model="gpt-4o-mini",
    response_format={"type": "json_schema", "schema": FactExtractionSchema},
    prompt=f"""
    Extract structured facts from this conversation that would be useful 
    to remember for future interactions with this user.
    
    Focus on: role, company, team, tech stack, preferences, goals, constraints.
    Only extract facts stated explicitly or clearly implied.
    Assign a confidence score 0-1.
    
    Conversation: {conversation_text}
    """
)
```

### 8.3 Contradiction Handling

When a new fact contradicts an existing one:

```
Existing: "preferred_language = Python" (confidence: 0.97, confirmed 3×)
New fact:  "preferred_language = TypeScript" (confidence: 0.85, 1 confirmation)

Strategy: "update"
Result:
  - Mark old fact as superseded
  - Store new fact
  - Create contradiction record for audit
  - In next session, may ask user to confirm
```

```json
{
  "long_term": {
    "contradiction_handling": "update"    // "update", "flag", "keep_both", "ask_user"
  }
}
```

---

## 9. Memory Management API

### 9.1 List Memory

```http
GET /api/v1/agents/{agent_id}/memory?user_id=user_456&type=semantic&limit=20
```

```json
{
  "data": [
    {
      "id": "smem_abc123",
      "type": "semantic",
      "summary": "User is building a RAG pipeline for legal document review...",
      "session_date": "2026-06-15",
      "relevance_to_last_query": 0.87,
      "topics": ["rag", "legal", "embeddings"]
    }
  ],
  "pagination": { "total": 47 }
}
```

### 9.2 Get Specific Memory Entry

```http
GET /api/v1/agents/{agent_id}/memory/{memory_id}
```

### 9.3 Store Memory

```http
POST /api/v1/agents/{agent_id}/memory
{
  "user_id": "user_456",
  "type": "long_term",
  "facts": [
    {
      "category": "preferences",
      "key": "output_format",
      "value": "Always provide code examples alongside explanations",
      "confidence": 1.0
    }
  ]
}
```

### 9.4 Update Memory Entry

```http
PATCH /api/v1/agents/{agent_id}/memory/{memory_id}
{
  "value": "Updated value",
  "confidence": 0.95
}
```

### 9.5 Delete Memory

```http
# Delete specific entry
DELETE /api/v1/agents/{agent_id}/memory/{memory_id}

# Clear all memory for a user
DELETE /api/v1/agents/{agent_id}/memory?user_id=user_456&type=all

# Clear by type
DELETE /api/v1/agents/{agent_id}/memory?user_id=user_456&type=episodic
```

### 9.6 Export Memory (GDPR / Audit)

```http
POST /api/v1/agents/{agent_id}/memory/export
{
  "user_id": "user_456",
  "format": "json",
  "include_types": ["episodic", "semantic", "long_term"]
}
```

**Response `202 Accepted`:**
```json
{
  "data": {
    "export_job_id": "export_abc123",
    "download_url": "https://storage.neuralcore.ai/exports/export_abc123.json",
    "expires_at": "2026-06-25T10:00:00Z"
  }
}
```

### 9.7 Python SDK

```python
# List all semantic memories for a user
memories = client.agents.memory.list(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    memory_type="semantic",
)

# Store a long-term fact
client.agents.memory.store(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    facts=[{"category": "preferences", "key": "language", "value": "Python"}]
)

# Search semantic memory
results = client.agents.memory.search(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    query="RAG pipeline discussions",
    top_k=5,
)

# Clear all episodic memory for a user
client.agents.memory.clear(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    memory_type="episodic",
)
```

---

## 10. Privacy & Data Isolation

### 10.1 Tenant & User Isolation

Memory is isolated at multiple levels:

```sql
-- All memory tables enforce tenant + user isolation at the DB level
CREATE TABLE agent_long_term_memory (
    id          UUID PRIMARY KEY,
    tenant_id   UUID NOT NULL,     -- Row-Level Security policy on this column
    agent_id    UUID NOT NULL,
    user_id     UUID NOT NULL,
    ...
);

-- RLS policy: users can only see their own tenant's data
CREATE POLICY memory_tenant_isolation ON agent_long_term_memory
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

Cross-user memory leakage is architecturally impossible — `user_id` is always required and enforced at query time.

### 10.2 Opt-Out

Users can opt out of memory collection:

```python
# Per-run opt-out
result = client.agents.run(
    agent_id="agent_9f3kd82",
    input="...",
    memory_options={"persist": False}   # Don't save this run to any memory layer
)

# Permanent opt-out for a user
client.agents.memory.opt_out(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    opt_out_types=["episodic", "semantic", "long_term"]
)
```

### 10.3 Data Retention Policies

```yaml
memory:
  retention:
    episodic:
      default_ttl_hours: 24
      max_ttl_hours: 720          # 30 days max
    semantic:
      default_ttl_days: 365
      max_ttl_days: 730           # 2 years max
    long_term:
      default_ttl_days: null      # Permanent
      max_ttl_days: 1825          # 5 years max
    gdpr_purge_on_request: true   # Delete all data within 72h of request
    auto_purge_inactive_users_days: 365
```

### 10.4 PII Handling in Memory

Before storing any memory, the PII detection pipeline scans for sensitive data:

```yaml
memory:
  pii:
    scan_before_store: true
    actions:
      email: redact
      phone: redact
      credit_card: block_storage
      ssn: block_storage
      name: flag
```

When `block_storage` is triggered, the turn is not stored in episodic or semantic memory.

---

## 11. Configuration Reference

```yaml
# config/memory.yaml

enabled: true
type: hybrid    # "working_only", "episodic", "semantic", "long_term", "hybrid"

working_memory:
  max_messages: 50
  max_tokens: 8000
  overflow_strategy: summarize
  summarization_model: gpt-4o-mini

episodic:
  enabled: true
  backend: redis
  session_ttl_hours: 24
  max_turns_per_session: 100
  max_sessions_retained: 20
  inject_last_n_turns: 10
  include_tool_calls: false
  compress_old_sessions: true

semantic:
  enabled: true
  backend: qdrant
  embedding_model: text-embedding-3-small
  dimensions: 1536
  summarize_after_turns: 10
  summarization_model: gpt-4o-mini
  top_k_retrieve: 5
  similarity_threshold: 0.72
  max_tokens_injected: 2000
  decay:
    enabled: true
    factor: 0.95
    period_days: 30

long_term:
  enabled: true
  backend: postgresql
  auto_extract: true
  extraction_model: gpt-4o-mini
  extract_after_turns: 10
  categories:
    - user_profile
    - preferences
    - context
    - decisions
  min_confidence: 0.80
  max_facts_per_user: 500
  contradiction_handling: update

injection:
  max_total_tokens: 4000
  long_term_max_tokens: 500
  episodic_max_tokens: 1000
  semantic_max_tokens: 2000
  include_timestamps: true
  format: structured              # "structured", "plain", "json"

privacy:
  pii_scan: true
  retention:
    episodic_ttl_hours: 24
    semantic_ttl_days: 365
  gdpr_purge_enabled: true
```

---

## 12. Performance & Scaling

### 12.1 Memory Operation Latencies

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Load episodic (last 10 turns) | 2–5ms | Redis GET |
| Load long-term facts | 1–3ms | PostgreSQL SELECT |
| Semantic memory search | 15–40ms | Qdrant ANN search |
| Total memory injection overhead | 20–50ms | Per agent run |
| Session summarization | 500–1500ms | Async, post-run |
| Fact extraction | 300–800ms | Async, post-run |

Memory injection adds ~20–50ms per agent run — a worthwhile trade-off for the quality improvement.

### 12.2 Storage Estimates

| Memory Type | Per User/Month | Per 100K Users |
|------------|---------------|----------------|
| Episodic (24h TTL) | < 1 MB | < 100 GB |
| Semantic (summaries) | 1–5 MB | 100–500 GB |
| Long-term facts | < 500 KB | < 50 GB |
| **Total** | **~5 MB** | **~650 GB** |

### 12.3 Scaling Considerations

**Redis (Episodic):**
- Use Redis Cluster for > 10M active users
- Enable Redis persistence (AOF) to survive restarts
- Set `maxmemory-policy: allkeys-lru` for automatic eviction

**Qdrant (Semantic):**
- Use separate Qdrant collection per agent (or per tenant)
- Enable collection-level quantization for storage efficiency
- Shard across Qdrant nodes for > 100M memory entries

**PostgreSQL (Long-term):**
- Partition `agent_long_term_memory` by `tenant_id`
- Index on `(agent_id, user_id, category)` for fast lookup
- Archive old facts (> 2 years) to cold storage

### 12.4 Cost Optimization

- Use `text-embedding-3-small` for semantic memory embedding (6× cheaper)
- Use `gpt-4o-mini` for summarization and fact extraction (20× cheaper than gpt-4o)
- Set aggressive TTLs on episodic memory for low-value interactions
- Enable semantic deduplication: don't store memories that are very similar to existing ones (`similarity_threshold: 0.95`)

---

*For memory architecture questions, GDPR compliance guidance, or custom memory backends, see [CONTRIBUTING.md](CONTRIBUTING.md) or open a GitHub issue tagged `area:memory`.*

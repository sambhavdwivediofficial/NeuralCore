# API Reference

NeuralCore exposes a versioned, production-grade REST API that powers the platform frontend, Python SDK, and all third-party integrations. This document is the authoritative reference for every endpoint, authentication scheme, request/response schema, and operational behavior.

**Base URL:** `https://api.neuralcore.ai` (cloud) or `http://localhost:8000` (self-hosted)

**Current version:** `v1`

**API prefix:** All endpoints are prefixed with `/api/v1/`

---

## 1. Authentication

NeuralCore supports two authentication mechanisms:

### 1.1 JWT Bearer Token (Session-based)

Obtained by authenticating through the `/api/v1/auth/login` endpoint. Tokens are short-lived (1 hour) and refresh automatically.

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**JWT Payload:**
```json
{
  "sub": "user_abc123",
  "email": "user@company.com",
  "role": "developer",
  "tenant_id": "tenant_xyz",
  "project_ids": ["proj_1", "proj_2"],
  "iat": 1718697600,
  "exp": 1718701200
}
```

### 1.2 API Key (Programmatic Access)

Long-lived keys for server-to-server integration. Generated via the dashboard or API. The secret is shown **once** at creation time.

```http
Authorization: Bearer nck_live_a1b2c3d4e5f6...
```

API keys are scoped to a project and optionally to specific endpoints.

### 1.3 Auth Endpoints

#### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@company.com",
  "password": "••••••••",
  "remember": true
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_abc123",
    "email": "user@company.com",
    "name": "Alice Smith",
    "role": "developer",
    "tenant_id": "tenant_xyz"
  }
}
```

Sets `nc_access_token` HTTP-only cookie. Access token also returned in response body for non-browser clients.

#### Refresh Token

```http
POST /api/v1/auth/refresh
Cookie: nc_access_token=...

{} 
```

**Response:** Same shape as login response.

#### Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

Revokes the refresh token and clears the session cookie.

#### MFA Verification

```http
POST /api/v1/auth/mfa/verify
Authorization: Bearer <token>

{
  "code": "123456",
  "mfa_token": "mfa_pending_token_from_login"
}
```

#### Password Reset

```http
POST /api/v1/auth/password/reset-request
{ "email": "user@company.com" }

POST /api/v1/auth/password/reset
{ "token": "<reset_token>", "new_password": "newpassword123" }
```

---

## 2. Request & Response Format

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <jwt_or_api_key>` |
| `Content-Type` | Yes (for POST/PATCH) | `application/json` |
| `X-Idempotency-Key` | No | UUID for safe retry of mutating requests |
| `X-Request-ID` | No | Client-provided trace ID (echoed in response) |

### Response Envelope

All successful responses follow this envelope:

```json
{
  "data": { ... },              
  "meta": {                     
    "request_id": "req_xyz789",
    "timestamp": "2026-06-18T10:00:00Z",
    "api_version": "v1"
  }
}
```

For lists:

```json
{
  "data": [ ... ],
  "meta": {
    "request_id": "req_xyz789",
    "timestamp": "2026-06-18T10:00:00Z"
  },
  "pagination": {
    "total": 847,
    "page": 1,
    "page_size": 20,
    "has_next": true,
    "has_prev": false,
    "next_cursor": "cursor_abc",
    "prev_cursor": null
  }
}
```

---

## 3. Pagination

All list endpoints support cursor-based pagination:

```http
GET /api/v1/agents?page_size=50&cursor=cursor_abc&sort_by=created_at&sort_order=desc
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page_size` | integer | 20 | Items per page (max: 100) |
| `cursor` | string | null | Opaque cursor from previous response |
| `sort_by` | string | `created_at` | Field to sort by |
| `sort_order` | string | `desc` | `asc` or `desc` |

---

## 4. Errors

### Error Response Shape

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body validation failed",
    "details": [
      {
        "field": "model.temperature",
        "issue": "Value must be between 0.0 and 2.0",
        "received": 3.5
      }
    ],
    "request_id": "req_xyz789",
    "docs_url": "https://docs.neuralcore.ai/errors/VALIDATION_ERROR"
  }
}
```

### Standard Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `VALIDATION_ERROR` | Request body or query params are invalid |
| 400 | `INVALID_JSON` | Malformed JSON in request body |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication token |
| 401 | `TOKEN_EXPIRED` | JWT has expired — refresh and retry |
| 403 | `FORBIDDEN` | Authenticated but insufficient permissions |
| 404 | `NOT_FOUND` | Resource with given ID does not exist |
| 409 | `CONFLICT` | Resource already exists or state conflict |
| 422 | `UNPROCESSABLE` | Request is syntactically valid but semantically wrong |
| 429 | `RATE_LIMITED` | Too many requests — see `Retry-After` header |
| 402 | `QUOTA_EXCEEDED` | Plan quota exceeded |
| 503 | `SERVICE_UNAVAILABLE` | Upstream dependency temporarily unavailable |
| 500 | `INTERNAL_ERROR` | Unexpected server error — report with `request_id` |

---

## 5. Rate Limiting

Rate limits are enforced per API key / user, per endpoint group:

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| Auth endpoints | 20 | 1 minute |
| Read operations (`GET`) | 1,000 | 1 minute |
| Write operations (`POST`, `PATCH`, `DELETE`) | 100 | 1 minute |
| Agent runs (`/run`, `/stream`) | 50 | 1 minute |
| Ingestion (`/documents`) | 20 | 1 minute |
| Embeddings API | 500 | 1 minute |

**Rate limit headers** (included in every response):

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1718701260
Retry-After: 23
```

When a limit is exceeded, the API returns `429 Too Many Requests`. Implement exponential backoff starting at 1 second.

---

## 6. Projects

Projects are the top-level organizational unit. All agents, knowledge bases, documents, and API keys belong to a project.

### 6.1 Create Project

```http
POST /api/v1/projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Customer Success Platform",
  "description": "AI agents for customer support, retention, and success workflows",
  "settings": {
    "default_llm_provider": "openai",
    "default_model": "gpt-4o",
    "cost_budget_usd_monthly": 500.00,
    "alert_threshold_pct": 80
  },
  "metadata": {
    "team": "growth",
    "environment": "production"
  }
}
```

**Response `201 Created`:**
```json
{
  "data": {
    "id": "proj_abc123",
    "name": "Customer Success Platform",
    "description": "...",
    "tenant_id": "tenant_xyz",
    "created_by": "user_abc",
    "created_at": "2026-06-18T10:00:00Z",
    "status": "active",
    "member_count": 1,
    "settings": { ... }
  }
}
```

### 6.2 List Projects

```http
GET /api/v1/projects?page_size=20&status=active
```

### 6.3 Get Project

```http
GET /api/v1/projects/{project_id}
```

### 6.4 Update Project

```http
PATCH /api/v1/projects/{project_id}
{
  "name": "Updated Name",
  "settings": {
    "cost_budget_usd_monthly": 1000.00
  }
}
```

### 6.5 Delete Project

```http
DELETE /api/v1/projects/{project_id}
```

Soft-delete. All resources under the project are deactivated. Hard deletion occurs after 30 days.

### 6.6 Project Analytics

```http
GET /api/v1/projects/{project_id}/analytics?range=7d
```

**Response:**
```json
{
  "data": {
    "period": {"start": "2026-06-11T00:00:00Z", "end": "2026-06-18T23:59:59Z"},
    "agent_runs": {"total": 8473, "success": 8312, "failed": 161},
    "token_usage": {"prompt": 12400000, "completion": 980000, "total": 13380000},
    "cost_usd": {"total": 287.43, "by_model": { "gpt-4o": 245.12, "gpt-4o-mini": 42.31 }},
    "avg_latency_ms": 3240,
    "p95_latency_ms": 8910,
    "active_agents": 12,
    "documents_processed": 341
  }
}
```

---

## 7. Agents

Full agent API. See [agents.md](agents.md) for conceptual documentation.

### 7.1 Create Agent

```http
POST /api/v1/agents
{
  "name": "Support Bot",
  "project_id": "proj_abc123",
  "type": "rag",
  "model": {
    "provider": "openai",
    "model_name": "gpt-4o",
    "temperature": 0.1,
    "max_tokens": 2048
  },
  "system_prompt": "You are a helpful support agent...",
  "tools": ["kb_retrieval", "http_request"],
  "knowledge_base_id": "kb_xyz789",
  "memory": { "enabled": true, "type": "hybrid" },
  "guardrails": {
    "max_iterations": 8,
    "max_cost_per_run_usd": 0.10,
    "timeout_seconds": 120
  }
}
```

### 7.2 List Agents

```http
GET /api/v1/agents?project_id=proj_abc123&type=rag&status=active
```

### 7.3 Run Agent

```http
POST /api/v1/agents/{agent_id}/run
{
  "input": "What is the refund policy for electronics?",
  "session_id": "session_user123",
  "user_id": "user_456",
  "context": {
    "user_plan": "premium",
    "channel": "web"
  }
}
```

**Response:**
```json
{
  "data": {
    "run_id": "run_abc123",
    "status": "success",
    "output": "Our electronics return policy allows returns within 15 days...",
    "citations": [ ... ],
    "steps_taken": 4,
    "token_usage": { "total": 3699 },
    "cost_usd": 0.0523,
    "latency_ms": 3240
  }
}
```

### 7.4 Stream Agent Run

```http
GET /api/v1/agents/{agent_id}/stream?input=<encoded>&session_id=<id>
Accept: text/event-stream
```

See [Section 17](#17-streaming-sse) for full SSE documentation.

### 7.5 Get Run Details

```http
GET /api/v1/agents/{agent_id}/runs/{run_id}
```

Returns full run trace including each ReAct step, tool calls, and token breakdown.

### 7.6 List Runs

```http
GET /api/v1/agents/{agent_id}/runs?status=success&limit=50&start_date=2026-06-01
```

### 7.7 Cancel Run

```http
POST /api/v1/agents/{agent_id}/runs/{run_id}/cancel
```

---

## 8. Knowledge Bases

A knowledge base (KB) is a versioned, searchable collection of documents backed by vector embeddings.

### 8.1 Create Knowledge Base

```http
POST /api/v1/knowledge-bases
{
  "name": "Product Documentation",
  "project_id": "proj_abc123",
  "description": "Complete product docs for Acme SaaS platform v4",
  "embedding": {
    "provider": "openai",
    "model": "text-embedding-3-large",
    "dimensions": 3072
  },
  "chunking": {
    "strategy": "semantic",
    "chunk_size": 512,
    "chunk_overlap": 64,
    "respect_boundaries": ["paragraph", "heading"]
  },
  "vector_store": {
    "backend": "qdrant",
    "collection_name": "product_docs_v4"
  },
  "metadata_schema": {
    "document_type": "string",
    "product_version": "string",
    "language": "string",
    "last_updated": "date"
  }
}
```

**Response `201 Created`:**
```json
{
  "data": {
    "id": "kb_xyz789",
    "name": "Product Documentation",
    "project_id": "proj_abc123",
    "status": "ready",
    "document_count": 0,
    "chunk_count": 0,
    "total_tokens": 0,
    "embedding": { ... },
    "vector_store": { ... },
    "created_at": "2026-06-18T10:00:00Z"
  }
}
```

### 8.2 List Knowledge Bases

```http
GET /api/v1/knowledge-bases?project_id=proj_abc123
```

### 8.3 Get Knowledge Base Stats

```http
GET /api/v1/knowledge-bases/{kb_id}/stats
```

```json
{
  "data": {
    "document_count": 1247,
    "chunk_count": 38492,
    "total_tokens": 14200000,
    "total_size_bytes": 52428800,
    "last_updated": "2026-06-17T14:30:00Z",
    "embedding_model": "text-embedding-3-large",
    "vector_dimensions": 3072,
    "index_health": "green"
  }
}
```

### 8.4 Delete Knowledge Base

```http
DELETE /api/v1/knowledge-bases/{kb_id}
```

Deletes all documents, chunks, and vector embeddings. Irreversible.

---

## 9. Documents & Ingestion

### 9.1 Upload Document

```http
POST /api/v1/knowledge-bases/{kb_id}/documents
Content-Type: multipart/form-data

file: <binary>
metadata: {
  "title": "Q4 2025 Product Changelog",
  "document_type": "changelog",
  "product_version": "4.2",
  "language": "en"
}
```

**Supported formats:** PDF, DOCX, TXT, MD, HTML, CSV, JSON, XLSX, PPTX

**Response `202 Accepted`:**
```json
{
  "data": {
    "document_id": "doc_abc123",
    "name": "Q4 2025 Product Changelog",
    "status": "processing",
    "ingestion_job_id": "job_xyz789",
    "estimated_completion_seconds": 45
  }
}
```

### 9.2 Ingest from URL

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/url
{
  "url": "https://docs.acme.com/api-reference",
  "crawler": {
    "follow_links": true,
    "max_depth": 3,
    "url_pattern": "https://docs.acme.com/*",
    "exclude_patterns": ["*/changelog/*", "*/blog/*"]
  },
  "refresh_interval_hours": 24,
  "metadata": { "source": "official_docs", "language": "en" }
}
```

### 9.3 Ingest from S3

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/s3
{
  "bucket": "acme-internal-docs",
  "prefix": "product/v4/",
  "file_extensions": [".pdf", ".md", ".docx"],
  "aws_region": "us-east-1",
  "credential_id": "cred_aws_abc123"
}
```

### 9.4 Get Ingestion Job Status

```http
GET /api/v1/ingestion-jobs/{job_id}
```

```json
{
  "data": {
    "id": "job_xyz789",
    "status": "completed",
    "progress": {
      "total_documents": 1,
      "processed": 1,
      "failed": 0
    },
    "result": {
      "document_id": "doc_abc123",
      "chunks_created": 47,
      "tokens_processed": 18200,
      "processing_time_ms": 3840
    }
  }
}
```

**Job statuses:** `queued` → `downloading` → `parsing` → `chunking` → `embedding` → `indexing` → `completed` | `failed`

### 9.5 List Documents

```http
GET /api/v1/knowledge-bases/{kb_id}/documents?status=ready&page_size=50
```

### 9.6 Delete Document

```http
DELETE /api/v1/knowledge-bases/{kb_id}/documents/{document_id}
```

Removes document and all its chunks and embeddings from the vector store.

### 9.7 Re-ingest Document

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/{document_id}/reingest
{
  "chunking": {
    "strategy": "fixed",
    "chunk_size": 256
  }
}
```

---

## 10. Retrieval

Query the knowledge base directly — useful for debugging, evaluation, and non-agent RAG workflows.

### 10.1 Semantic Search

```http
POST /api/v1/knowledge-bases/{kb_id}/retrieve
{
  "query": "What is the refund policy for electronics?",
  "strategy": "hybrid",
  "top_k": 10,
  "filters": {
    "metadata": {
      "document_type": "policy",
      "language": "en"
    }
  },
  "reranking": {
    "enabled": true,
    "top_k_after_rerank": 5
  },
  "min_similarity_score": 0.70,
  "include_metadata": true,
  "include_embeddings": false
}
```

**Response:**
```json
{
  "data": {
    "query": "What is the refund policy for electronics?",
    "strategy_used": "hybrid",
    "results": [
      {
        "rank": 1,
        "chunk_id": "chunk_abc001",
        "document_id": "doc_policy_001",
        "document_title": "Electronics Return Policy",
        "text": "Electronic devices purchased from Acme may be returned within 15 days...",
        "similarity_score": 0.921,
        "rerank_score": 0.887,
        "metadata": {
          "document_type": "policy",
          "page_number": 3,
          "language": "en"
        }
      }
    ],
    "total_results": 5,
    "retrieval_latency_ms": 89,
    "reranking_latency_ms": 134
  }
}
```

### 10.2 Retrieval Debug Mode

```http
POST /api/v1/knowledge-bases/{kb_id}/retrieve/debug
{
  "query": "refund policy electronics",
  "strategy": "hybrid",
  "top_k": 10
}
```

Returns extended debug info including BM25 scores, vector scores, reranker scores, and which chunks were filtered.

---

## 11. Embeddings

Generate embeddings using NeuralCore's managed embedding pipeline.

### 11.1 Embed Text

```http
POST /api/v1/embeddings
{
  "input": "What is machine learning?",
  "model": "text-embedding-3-large",
  "dimensions": 3072,
  "encoding_format": "float"
}
```

**Response:**
```json
{
  "data": {
    "embedding": [0.0023, -0.0147, ...],
    "model": "text-embedding-3-large",
    "dimensions": 3072,
    "token_count": 5,
    "latency_ms": 43
  }
}
```

### 11.2 Batch Embed

```http
POST /api/v1/embeddings/batch
{
  "inputs": ["text one", "text two", "text three"],
  "model": "text-embedding-3-large",
  "dimensions": 1536
}
```

Max 2,048 inputs per batch. Returns an array of embeddings in the same order as inputs.

### 11.3 Similarity Score

```http
POST /api/v1/embeddings/similarity
{
  "text_a": "The product is excellent",
  "text_b": "I love this item",
  "model": "text-embedding-3-large"
}
```

**Response:**
```json
{
  "data": {
    "cosine_similarity": 0.847,
    "distance": 0.153
  }
}
```

---

## 12. Vector Stores

Manage vector store collections directly (advanced usage).

### 12.1 List Collections

```http
GET /api/v1/vector-stores/{backend}/collections
```

`backend`: `qdrant` | `pgvector` | `milvus`

### 12.2 Create Collection

```http
POST /api/v1/vector-stores/{backend}/collections
{
  "name": "my_collection",
  "dimensions": 1536,
  "distance_metric": "cosine",
  "indexing_config": {
    "type": "hnsw",
    "m": 16,
    "ef_construction": 200
  }
}
```

### 12.3 Get Collection Info

```http
GET /api/v1/vector-stores/{backend}/collections/{collection_name}
```

### 12.4 Delete Collection

```http
DELETE /api/v1/vector-stores/{backend}/collections/{collection_name}
```

---

## 13. Users & Teams

### 13.1 Get Current User

```http
GET /api/v1/users/me
```

```json
{
  "data": {
    "id": "user_abc123",
    "email": "alice@company.com",
    "name": "Alice Smith",
    "role": "developer",
    "tenant_id": "tenant_xyz",
    "avatar_url": null,
    "mfa_enabled": true,
    "created_at": "2026-01-15T09:00:00Z",
    "last_login_at": "2026-06-18T08:30:00Z"
  }
}
```

### 13.2 Update Profile

```http
PATCH /api/v1/users/me
{
  "name": "Alice Johnson",
  "notification_preferences": {
    "email_on_run_failure": true,
    "email_on_cost_alert": true,
    "slack_webhook_url": "https://hooks.slack.com/..."
  }
}
```

### 13.3 List Team Members

```http
GET /api/v1/team/members?project_id=proj_abc123
```

### 13.4 Invite Team Member

```http
POST /api/v1/team/invite
{
  "email": "bob@company.com",
  "role": "viewer",
  "project_ids": ["proj_abc123"],
  "message": "Welcome to the NeuralCore team!"
}
```

**Roles:**

| Role | Permissions |
|------|------------|
| `viewer` | Read agents, runs, KBs; no write access |
| `developer` | Create/update agents, KBs, documents; run agents |
| `admin` | Full project control; manage members; billing |
| `owner` | All admin rights + delete project, manage all users |

### 13.5 Update Member Role

```http
PATCH /api/v1/team/members/{user_id}
{ "role": "developer" }
```

### 13.6 Remove Member

```http
DELETE /api/v1/team/members/{user_id}
```

---

## 14. API Keys

### 14.1 Create API Key

```http
POST /api/v1/api-keys
{
  "name": "Production Integration Key",
  "project_id": "proj_abc123",
  "scopes": ["agents:run", "knowledge-bases:read"],
  "expires_at": "2027-06-18T00:00:00Z",
  "ip_allowlist": ["203.0.113.0/24"]
}
```

**Response `201 Created`** — secret shown once:
```json
{
  "data": {
    "id": "key_abc123",
    "name": "Production Integration Key",
    "key": "nck_live_a1b2c3d4e5f6g7h8i9j0...",
    "prefix": "nck_live_a1b2",
    "project_id": "proj_abc123",
    "scopes": ["agents:run", "knowledge-bases:read"],
    "created_at": "2026-06-18T10:00:00Z",
    "expires_at": "2027-06-18T00:00:00Z"
  },
  "warning": "Store this key securely. It will not be shown again."
}
```

### 14.2 List API Keys

```http
GET /api/v1/api-keys?project_id=proj_abc123
```

Returns key metadata only — secret is never returned after creation.

### 14.3 Revoke API Key

```http
DELETE /api/v1/api-keys/{key_id}
```

Immediate effect. All in-flight requests using this key will fail after revocation.

---

## 15. Monitoring & Analytics

### 15.1 Platform Health

```http
GET /health
```

```json
{
  "status": "healthy",
  "version": "1.4.2",
  "timestamp": "2026-06-18T10:00:00Z",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "qdrant": "healthy",
    "llm_providers": {
      "openai": "healthy",
      "anthropic": "healthy"
    }
  }
}
```

### 15.2 Project Analytics

```http
GET /api/v1/analytics/projects/{project_id}?range=30d&granularity=day
```

### 15.3 Agent Analytics

```http
GET /api/v1/analytics/agents/{agent_id}?range=7d&granularity=hour
```

**Response:**
```json
{
  "data": {
    "period": { "start": "...", "end": "..." },
    "granularity": "hour",
    "series": [
      {
        "timestamp": "2026-06-18T09:00:00Z",
        "runs": 142,
        "success_rate": 0.977,
        "avg_latency_ms": 3120,
        "p95_latency_ms": 8700,
        "tokens_used": 487200,
        "cost_usd": 6.84
      }
    ],
    "totals": {
      "runs": 8473,
      "success_rate": 0.981,
      "avg_latency_ms": 3240,
      "total_tokens": 13380000,
      "total_cost_usd": 287.43
    }
  }
}
```

### 15.4 Cost Analytics

```http
GET /api/v1/analytics/costs?project_id=proj_abc123&range=30d&group_by=agent
```

### 15.5 Logs

```http
GET /api/v1/monitoring/logs?project_id=proj_abc123&level=error&limit=100&start_date=2026-06-01
```

### 15.6 Traces

```http
GET /api/v1/monitoring/traces?agent_id=agent_abc&min_latency_ms=5000&limit=50
```

---

## 16. Webhooks

Subscribe to NeuralCore events for real-time integration.

### 16.1 Create Webhook

```http
POST /api/v1/webhooks
{
  "url": "https://your-service.com/webhooks/neuralcore",
  "events": [
    "agent.run.completed",
    "agent.run.failed",
    "ingestion.document.processed",
    "cost.budget.threshold_reached"
  ],
  "project_id": "proj_abc123",
  "secret": "your_signing_secret",
  "active": true
}
```

### 16.2 Webhook Payload

```json
{
  "id": "evt_abc123",
  "type": "agent.run.completed",
  "created_at": "2026-06-18T10:00:12Z",
  "data": {
    "agent_id": "agent_9f3kd82",
    "run_id": "run_abc123",
    "status": "success",
    "output": "...",
    "cost_usd": 0.0523,
    "latency_ms": 3240
  }
}
```

### 16.3 Signature Verification

Every webhook delivery includes an `X-NeuralCore-Signature` header. Verify it:

```python
import hmac, hashlib

def verify_webhook(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)
```

### 16.4 Available Events

| Event | Trigger |
|-------|---------|
| `agent.run.completed` | Agent run finished successfully |
| `agent.run.failed` | Agent run failed or was cancelled |
| `agent.run.timed_out` | Agent run exceeded timeout |
| `agent.guardrail.triggered` | Safety guardrail blocked a run |
| `ingestion.document.processed` | Document ingestion completed |
| `ingestion.document.failed` | Document ingestion failed |
| `kb.created` | New knowledge base created |
| `cost.budget.threshold_reached` | Project cost reached alert threshold |
| `team.member.invited` | Team member invited |
| `api_key.revoked` | API key was revoked |

---

## 17. Streaming (SSE)

Agent runs support real-time streaming via Server-Sent Events.

### 17.1 Connect to Stream

```http
GET /api/v1/agents/{agent_id}/stream
Authorization: Bearer <token>
Accept: text/event-stream
Cache-Control: no-cache
X-Run-Input: <URL-encoded input>
X-Session-ID: session_user123
```

Or via POST for long inputs:

```http
POST /api/v1/agents/{agent_id}/stream
Content-Type: application/json

{ "input": "...", "session_id": "session_user123" }
```

### 17.2 Event Format

```
id: evt_001
event: llm.token
data: {"content": "Our"}

id: evt_002
event: llm.token
data: {"content": " electronics"}

id: evt_003
event: tool.called
data: {"tool_name": "kb_retrieval", "tool_input": {"query": "electronics return policy"}}

id: evt_004
event: tool.result
data: {"tool_name": "kb_retrieval", "result_count": 5, "latency_ms": 89}

id: evt_005
event: run.done
data: {"run_id": "run_abc123", "status": "success", "steps_taken": 4, "cost_usd": 0.0523}
```

### 17.3 Reconnection

If the connection drops mid-stream, reconnect using the `Last-Event-ID` header:

```http
GET /api/v1/agents/{agent_id}/stream
Last-Event-ID: evt_003
```

The server resumes from the last delivered event.

---

## 18. OpenAPI Spec

The full OpenAPI 3.1 spec is available at:

```
GET /api/v1/openapi.json
GET /api/v1/openapi.yaml
```

Interactive Swagger UI: `http://localhost:8000/docs`

ReDoc: `http://localhost:8000/redoc`

### Generating a Client

```bash
# TypeScript
npx openapi-typescript http://localhost:8000/api/v1/openapi.json -o src/types/api.d.ts

# Python
pip install openapi-python-client
openapi-python-client generate --url http://localhost:8000/api/v1/openapi.json

# Go
go install github.com/deepmap/oapi-codegen/cmd/oapi-codegen@latest
oapi-codegen -package neuralcore http://localhost:8000/api/v1/openapi.json > neuralcore.gen.go
```

---

*For authentication issues, rate limit increases, or enterprise API access, contact support@neuralcore.ai or visit the [developer portal](https://developers.neuralcore.ai).*

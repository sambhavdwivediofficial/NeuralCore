# Document Ingestion

NeuralCore's ingestion pipeline transforms raw documents — PDFs, Word files, web pages, code repositories, databases, and more — into semantically indexed, retrievable knowledge. This document covers every stage of the pipeline, from source connectors to vector indexing, with full configuration and operational guidance.

---

## 1. Overview

The ingestion pipeline is the foundation of every NeuralCore knowledge base. Its job is to take unstructured or semi-structured content from any source and convert it into a form that can be efficiently and accurately retrieved by agents and users.

### What Ingestion Does

```
Raw Source Content
        │
        ▼
[Parse]  Extract clean text from any format (PDF, HTML, DOCX, etc.)
        │
        ▼
[Clean]  Remove noise, normalize whitespace, detect language
        │
        ▼
[Chunk]  Split text into semantically coherent units
        │
        ▼
[Enrich] Add metadata, extract entities, detect topics
        │
        ▼
[Embed]  Convert each chunk to a dense vector embedding
        │
        ▼
[Index]  Store vector + metadata in Qdrant + PostgreSQL
        │
        ▼
Knowledge Base — Ready for retrieval
```

### Key Properties

- **Async by default** — All ingestion runs as background Celery tasks. No blocking API calls.
- **Idempotent** — Re-ingesting the same document is safe; it replaces the previous version.
- **Format-agnostic** — 30+ file formats supported via a unified parser abstraction.
- **Incremental** — Only changed documents are re-processed in sync jobs.
- **Observable** — Every job has progress tracking, per-document status, and full error logs.

---

## 2. Ingestion Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Ingestion Pipeline                              │
│                                                                     │
│  ┌──────────────┐                                                   │
│  │   Ingestion  │  REST API / SDK / Connector / Scheduler          │
│  │   Trigger    │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐    Celery Queue (Redis)                          │
│  │  Job Manager │◀──────────────────────────────────────────────┐  │
│  │  - validate  │                                               │  │
│  │  - enqueue   │                                               │  │
│  │  - track     │                                               │  │
│  └──────┬───────┘                                               │  │
│         │                                                       │  │
│         ▼                                                       │  │
│  ┌──────────────────────────────────────────────────────────┐   │  │
│  │                  Ingestion Worker                        │   │  │
│  │                                                          │   │  │
│  │  [1. Download / Fetch]                                   │   │  │
│  │       ↓                                                  │   │  │
│  │  [2. Parse & Extract]  → PDF, DOCX, HTML, MD, CSV...     │   │  │
│  │       ↓                                                  │   │  │
│  │  [3. Clean & Normalize]                                  │   │  │
│  │       ↓                                                  │   │  │
│  │  [4. Language Detection]                                 │   │  │
│  │       ↓                                                  │   │  │
│  │  [5. Chunk]            → Fixed / Semantic / Recursive    │   │  │
│  │       ↓                                                  │   │  │
│  │  [6. Metadata Enrichment] → entities, topics, summary   │   │  │
│  │       ↓                                                  │   │  │
│  │  [7. Deduplicate]      → Skip unchanged chunks           │   │  │
│  │       ↓                                                  │   │  │
│  │  [8. Embed]            → Batch embed all new chunks      │   │  │
│  │       ↓                                                  │   │  │
│  │  [9. Index]            → Qdrant + PostgreSQL             │   │  │
│  │       ↓                                                  │   │  │
│  │  [10. Update Job Status]                                 │   │  │
│  └──────────────────────────────────────────────────────────┘   │  │
│                                                                  │  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │  │
│  │  PostgreSQL  │  │    Qdrant    │  │    Redis (cache)     │   │  │
│  │  (metadata)  │  │  (vectors)   │  │   (job status)       │   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Supported Source Types

### 3.1 File Formats

| Format | Parser | Notes |
|--------|--------|-------|
| PDF | PyMuPDF + pdfplumber | Tables, images, multi-column layouts |
| DOCX / DOC | python-docx | Styles, tables, headers/footers |
| PPTX | python-pptx | Slide text, speaker notes |
| XLSX / CSV | pandas | Tabular data → text or row-per-chunk |
| HTML | BeautifulSoup + trafilatura | Boilerplate removal, main content extraction |
| Markdown | mistune | Preserves headings for semantic chunking |
| Plain text | native | UTF-8, Latin-1 auto-detected |
| JSON / JSONL | native | Path-based field extraction |
| XML | lxml | XPath-based field extraction |
| EPUB | ebooklib | Chapter-aware splitting |
| RTF | striprtf | Basic text extraction |
| MSG / EML | extract-msg | Email metadata + body |

### 3.2 Remote Sources

| Source | Protocol | Authentication |
|--------|----------|---------------|
| URL / website | HTTP/HTTPS | None, Basic, Bearer, Cookie |
| Web crawler | HTTP/HTTPS | None, Basic, Bearer |
| S3 / S3-compatible | AWS SDK | IAM role, Access Key |
| Google Cloud Storage | GCS SDK | Service account |
| Azure Blob Storage | Azure SDK | Connection string, MI |
| SFTP | paramiko | Key, password |
| FTP | ftplib | Username/password |

### 3.3 Application Connectors (see [Section 11](#11-source-connectors))

Confluence, Notion, Google Drive, Dropbox, SharePoint, GitHub, GitLab, Jira, Zendesk, Intercom, Slack, and more.

---

## 4. Ingestion via API

### 4.1 Upload File

```http
POST /api/v1/knowledge-bases/{kb_id}/documents
Authorization: Bearer <token>
Content-Type: multipart/form-data

------FormBoundary
Content-Disposition: form-data; name="file"; filename="product_manual.pdf"
Content-Type: application/pdf

<binary content>
------FormBoundary
Content-Disposition: form-data; name="metadata"
Content-Type: application/json

{
  "title": "Product Manual v3.2",
  "document_type": "manual",
  "product_version": "3.2",
  "language": "en",
  "department": "engineering"
}
------FormBoundary--
```

**Response `202 Accepted`:**
```json
{
  "data": {
    "document_id": "doc_abc123",
    "knowledge_base_id": "kb_xyz789",
    "name": "product_manual.pdf",
    "status": "queued",
    "ingestion_job_id": "job_def456",
    "file_size_bytes": 2458624,
    "mime_type": "application/pdf",
    "estimated_completion_seconds": 30
  }
}
```

### 4.2 Ingest from URL

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/url
{
  "url": "https://docs.yourproduct.com/api-reference",
  "title": "API Reference Docs",
  "crawler": {
    "enabled": false
  },
  "metadata": {
    "document_type": "api_docs",
    "source": "official_website"
  }
}
```

### 4.3 Crawl Website

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/crawl
{
  "start_url": "https://docs.yourproduct.com",
  "config": {
    "max_pages": 500,
    "max_depth": 4,
    "follow_external_links": false,
    "url_include_patterns": ["https://docs.yourproduct.com/*"],
    "url_exclude_patterns": [
      "*/blog/*",
      "*/changelog/*",
      "*/search*",
      "*.pdf"
    ],
    "respect_robots_txt": true,
    "rate_limit_rps": 2,
    "user_agent": "NeuralCore-Crawler/1.0 (+https://neuralcore.ai/bot)"
  },
  "refresh_interval_hours": 24,
  "metadata": {
    "source_type": "documentation",
    "language": "en"
  }
}
```

### 4.4 Ingest from S3

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/s3
{
  "bucket": "company-documents",
  "prefix": "product-docs/v4/",
  "file_extensions": [".pdf", ".docx", ".md"],
  "recursive": true,
  "aws_region": "us-east-1",
  "credential_id": "cred_aws_abc123",
  "metadata_from_path": {
    "pattern": "product-docs/{version}/{category}/{filename}",
    "fields": ["version", "category"]
  },
  "refresh_interval_hours": 12
}
```

### 4.5 Python SDK

```python
from neuralcore import NeuralCoreClient
from pathlib import Path

client = NeuralCoreClient(api_key="nck_...")

# Upload single file
with open("document.pdf", "rb") as f:
    doc = client.knowledge_bases.ingest_file(
        kb_id="kb_xyz789",
        file=f,
        filename="document.pdf",
        metadata={"document_type": "policy", "version": "2.1"}
    )

# Upload entire directory
results = client.knowledge_bases.ingest_directory(
    kb_id="kb_xyz789",
    directory=Path("./docs"),
    recursive=True,
    file_extensions=[".pdf", ".md", ".docx"],
    metadata={"source": "local_export"},
)

print(f"Submitted {len(results)} documents for ingestion")

# Wait for completion
for result in results:
    job = client.ingestion_jobs.wait(result.ingestion_job_id, timeout=300)
    print(f"{result.name}: {job.status} ({job.result.chunks_created} chunks)")
```

---

## 5. Parsing & Extraction

### 5.1 PDF Parsing

PDFs are the most complex format due to their varied internal structure:

```yaml
# config/ingestion/pdf.yaml
pdf:
  parser: "pymupdf"              # "pymupdf", "pdfplumber", "unstructured"
  extract_images: false          # OCR images to text (slow, requires Tesseract)
  extract_tables: true           # Convert tables to markdown
  table_format: "markdown"       # "markdown", "csv", "plain"
  extract_headers_footers: false # Skip repeated page headers/footers
  merge_hyphenated_words: true   # "hyphen-\nated" → "hyphenated"
  preserve_page_breaks: true     # Add page number metadata per chunk
  ocr:
    enabled: false               # Enable for scanned PDFs
    language: "eng"
    engine: "tesseract"          # "tesseract", "paddleocr", "azure"
    dpi: 300
```

### 5.2 HTML Parsing

```yaml
html:
  extractor: "trafilatura"       # "trafilatura", "readability", "beautifulsoup"
  remove_boilerplate: true       # Remove nav, footer, ads
  extract_metadata: true         # title, description, og:* tags
  preserve_structure: true       # Keep heading hierarchy
  min_content_length: 100        # Skip pages with < 100 chars
```

### 5.3 Tabular Data (CSV / Excel)

Two strategies for tabular data:

**Row-per-document** — Each row becomes an independently retrievable document:
```json
{
  "csv": {
    "strategy": "row_per_document",
    "row_template": "Product: {product_name}. Category: {category}. Price: ${price}. Description: {description}",
    "include_columns": ["product_name", "category", "price", "description"],
    "skip_empty_rows": true
  }
}
```

**Whole-table** — Entire table converted to markdown:
```json
{
  "csv": {
    "strategy": "markdown_table",
    "max_rows": 200,
    "chunk_size_rows": 50
  }
}
```

---

## 6. Chunking Strategies

Chunking splits documents into the right-sized units for embedding and retrieval. The goal: each chunk should be semantically complete and independently retrievable.

### 6.1 Strategy Comparison

| Strategy | Description | Best For | Chunk Size |
|----------|-------------|----------|-----------|
| `fixed` | Split every N tokens with K overlap | Simple, fast | 256–512 tokens |
| `recursive` | Split on `\n\n`, `\n`, `. `, ` ` in order | General text | 256–512 tokens |
| `semantic` | Use embedding similarity to find natural boundaries | High-quality retrieval | Variable |
| `markdown` | Split on headings (H1/H2/H3) | Documentation, wikis | Variable |
| `sentence` | Split on sentence boundaries (spaCy) | Q&A, fine-grained retrieval | 1–10 sentences |
| `paragraph` | Split on blank lines | Articles, books | Variable |
| `code` | Language-aware splitting (AST-based) | Code documentation | Function/class level |
| `html` | Split on HTML block elements | Web content | Variable |
| `page` | One chunk per PDF page | Dense technical PDFs | Whole page |

### 6.2 Configuration

```json
{
  "chunking": {
    "strategy": "semantic",
    "chunk_size": 512,
    "chunk_overlap": 64,
    "min_chunk_size": 50,
    "max_chunk_size": 1024,
    "respect_boundaries": ["paragraph", "heading", "sentence"],
    "include_metadata_in_chunk": false,
    "prepend_document_title": true,
    "prepend_section_heading": true
  }
}
```

### 6.3 Semantic Chunking (Recommended)

Semantic chunking uses embedding similarity to find natural topic boundaries — instead of splitting at arbitrary token counts, it splits where meaning changes:

```
Paragraph 1: "Machine learning is a subset of AI..."
Paragraph 2: "Deep learning uses neural networks..."
Paragraph 3: "Return policy: items can be returned..."  ← Topic change here

Fixed chunking: might split paragraph 2 in the middle
Semantic chunking: always splits at the topic boundary (para 3 start)
```

Semantic chunking improves retrieval precision by 10–25% but takes 2–4× longer to run.

### 6.4 Context Window Injection

For each chunk, NeuralCore can prepend surrounding context to preserve coherence:

```json
{
  "chunking": {
    "context_injection": {
      "enabled": true,
      "prepend_document_title": true,
      "prepend_section_headings": true,
      "prepend_summary": false,
      "summary_max_tokens": 100
    }
  }
}
```

**Result:**
```
[Document: NeuralCore API Reference > Section: Authentication > Subsection: JWT Tokens]

JWT tokens are issued upon successful login and expire after 1 hour. The token payload 
includes the user ID, role, tenant ID, and project scopes...
```

---

## 7. Metadata Enrichment

After parsing and chunking, NeuralCore can automatically enrich each chunk with structured metadata:

### 7.1 Auto-Extracted Metadata

```yaml
metadata_enrichment:
  language_detection:
    enabled: true
    model: "fasttext"           # "fasttext", "langdetect", "openai"

  entity_extraction:
    enabled: true
    model: "en_core_web_trf"    # spaCy model
    entity_types:
      - PERSON
      - ORG
      - PRODUCT
      - DATE
      - MONEY
      - GPE                     # Geopolitical entity

  topic_classification:
    enabled: true
    model: "zero_shot"
    labels: ["technical", "legal", "financial", "support", "marketing"]
    threshold: 0.7

  summary_generation:
    enabled: true
    model: "gpt-4o-mini"
    max_tokens: 100
    only_for_chunks_larger_than: 300  # tokens
```

### 7.2 Resulting Chunk Metadata

```json
{
  "chunk_id": "chunk_abc001",
  "document_id": "doc_abc123",
  "knowledge_base_id": "kb_xyz789",
  "text": "The refund policy for electronics...",
  "token_count": 187,
  "chunk_index": 4,
  "page_number": 3,
  "metadata": {
    "document_title": "Return Policy Guide",
    "document_type": "policy",
    "section_heading": "Electronics Returns",
    "language": "en",
    "language_confidence": 0.99,
    "entities": {
      "ORG": ["Acme Corp"],
      "PRODUCT": ["electronics", "smartphones"]
    },
    "topics": [{"label": "legal", "score": 0.87}],
    "auto_summary": "Electronics must be returned within 15 days with original packaging.",
    "created_at": "2026-06-18T10:00:00Z",
    "source_url": "https://docs.acme.com/policies/returns"
  }
}
```

### 7.3 Custom Metadata

You can inject arbitrary metadata at ingestion time, which is then filterable at retrieval time:

```python
client.knowledge_bases.ingest_file(
    kb_id="kb_xyz789",
    file=open("contract.pdf", "rb"),
    metadata={
        "document_type": "contract",
        "client_name": "Acme Corp",
        "contract_value_usd": 500000,
        "effective_date": "2026-01-01",
        "jurisdiction": "California",
        "confidentiality": "internal"
    }
)
```

Then filter at retrieval:
```json
{
  "filters": {
    "metadata": {
      "document_type": "contract",
      "jurisdiction": "California",
      "contract_value_usd": {"gte": 100000}
    }
  }
}
```

---

## 8. Embedding & Indexing

After chunking and enrichment, each chunk is embedded and stored in the vector index.

### 8.1 Embedding Configuration per Knowledge Base

```json
{
  "embedding": {
    "provider": "openai",
    "model": "text-embedding-3-large",
    "dimensions": 1536,
    "batch_size": 100,
    "normalize": true,
    "text_template": "{title}\n\n{text}"
  }
}
```

The `text_template` controls what text is actually embedded — you can include the document title, section heading, or custom metadata fields alongside the chunk text for richer representation.

### 8.2 Dual Embedding (Hybrid Retrieval)

For maximum retrieval quality, NeuralCore can embed each chunk with two models simultaneously — a dense embedding model and a sparse BM25 index — enabling hybrid retrieval:

```json
{
  "embedding": {
    "dense": {
      "provider": "openai",
      "model": "text-embedding-3-large",
      "dimensions": 1536
    },
    "sparse": {
      "type": "bm25",
      "language": "en",
      "k1": 1.5,
      "b": 0.75
    }
  },
  "retrieval": {
    "strategy": "hybrid",
    "alpha": 0.7   // 70% dense + 30% sparse weight
  }
}
```

### 8.3 Indexing Targets

| Target | Use Case | Storage |
|--------|----------|---------|
| Qdrant | Primary vector search | Disk-backed |
| pgvector | Metadata-filtered search | PostgreSQL |
| Both | Full hybrid capability | Both |

---

## 9. Deduplication

### 9.1 Document-Level Deduplication

When re-ingesting a document, NeuralCore computes a content hash and skips re-embedding if the content is unchanged:

```
Document Hash (SHA-256)
    │
    ▼
Match in database?
    ├── Yes + hash identical → Skip (no cost incurred)
    └── No / hash changed → Full re-ingest (update all chunks)
```

### 9.2 Chunk-Level Deduplication

Within a knowledge base, near-duplicate chunks from different documents are detected and flagged:

```yaml
deduplication:
  document_level:
    enabled: true
    hash_fields: ["content", "url"]     # Fields to hash for identity check

  chunk_level:
    enabled: true
    similarity_threshold: 0.99          # Cosine similarity
    action: "skip"                      # "skip", "merge", "flag"
    embedding_model: "text-embedding-3-small"   # Use cheap model for dedup
```

### 9.3 Re-ingestion Behavior

```
Re-ingest request for doc_abc123
              │
    Content hash matches?
         │
    ┌────┴────┐
   Yes       No
    │         │
  Skip      Delete old chunks
  (return   Insert new chunks
  200 OK)   Update metadata
              │
           200 OK
```

---

## 10. Scheduled & Continuous Ingestion

### 10.1 Refresh Schedules

Set a document or crawl source to auto-refresh:

```json
{
  "refresh": {
    "enabled": true,
    "interval": "24h",         // "1h", "6h", "24h", "7d"
    "strategy": "incremental", // "full" or "incremental"
    "at": "02:00",             // UTC time for daily refresh
    "timezone": "UTC",
    "max_age_days": 7          // Re-ingest documents older than N days
  }
}
```

### 10.2 Webhook-Triggered Ingestion

Trigger ingestion via webhook when your CMS publishes new content:

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/webhook
X-NeuralCore-Webhook-Secret: your_secret

{
  "event": "content.published",
  "document": {
    "url": "https://docs.acme.com/new-page",
    "title": "New Feature Announcement",
    "updated_at": "2026-06-18T10:00:00Z"
  }
}
```

### 10.3 Real-Time Sync (Event Streaming)

For real-time knowledge base updates via Kafka or SQS:

```yaml
# config/connectors/kafka.yaml
kafka:
  enabled: true
  bootstrap_servers: "kafka:9092"
  topic: "document_events"
  group_id: "neuralcore-ingestion"
  auto_offset_reset: "latest"
  event_types:
    - "document.created"
    - "document.updated"
    - "document.deleted"
  knowledge_base_id: "kb_xyz789"
```

---

## 11. Source Connectors

### 11.1 Confluence

```json
{
  "connector": "confluence",
  "config": {
    "base_url": "https://yourorg.atlassian.net/wiki",
    "username": "admin@yourorg.com",
    "api_token": "{{env.CONFLUENCE_API_TOKEN}}",
    "spaces": ["ENG", "PRODUCT", "SUPPORT"],
    "include_page_types": ["page", "blogpost"],
    "include_comments": false,
    "exclude_labels": ["draft", "archived"],
    "max_pages": 5000,
    "refresh_interval_hours": 6
  }
}
```

### 11.2 Notion

```json
{
  "connector": "notion",
  "config": {
    "integration_token": "{{env.NOTION_TOKEN}}",
    "database_ids": ["abc123", "def456"],
    "page_ids": [],
    "include_child_pages": true,
    "exclude_properties": ["internal_notes"],
    "refresh_interval_hours": 12
  }
}
```

### 11.3 Google Drive

```json
{
  "connector": "google_drive",
  "config": {
    "service_account_json": "{{env.GOOGLE_SERVICE_ACCOUNT}}",
    "folder_ids": ["1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"],
    "file_types": ["application/pdf", "application/vnd.google-apps.document"],
    "recursive": true,
    "refresh_interval_hours": 24
  }
}
```

### 11.4 GitHub

```json
{
  "connector": "github",
  "config": {
    "access_token": "{{env.GITHUB_TOKEN}}",
    "repositories": ["yourorg/product", "yourorg/docs"],
    "branches": ["main"],
    "file_patterns": ["docs/**/*.md", "README.md", "*.md"],
    "exclude_patterns": ["node_modules/**", ".github/**"],
    "include_commit_messages": false,
    "refresh_on_push": true
  }
}
```

### 11.5 Zendesk

```json
{
  "connector": "zendesk",
  "config": {
    "subdomain": "yourcompany",
    "email": "admin@yourcompany.com",
    "api_token": "{{env.ZENDESK_TOKEN}}",
    "sources": ["help_center_articles", "ticket_comments"],
    "help_center": {
      "locales": ["en-US"],
      "categories": ["Getting Started", "Troubleshooting"],
      "min_votes": 5,
      "published_only": true
    },
    "tickets": {
      "tags": ["public-knowledge"],
      "solved_only": true,
      "max_tickets": 10000
    }
  }
}
```

---

## 12. Ingestion Jobs & Monitoring

### 12.1 Job Status API

```http
GET /api/v1/ingestion-jobs/{job_id}
```

**Response:**
```json
{
  "data": {
    "id": "job_def456",
    "document_id": "doc_abc123",
    "knowledge_base_id": "kb_xyz789",
    "status": "embedding",
    "started_at": "2026-06-18T10:00:00Z",
    "updated_at": "2026-06-18T10:00:42Z",
    "progress": {
      "stage": "embedding",
      "stages_completed": ["download", "parse", "clean", "chunk", "enrich"],
      "stages_remaining": ["embedding", "index"],
      "total_chunks": 148,
      "chunks_embedded": 87,
      "percent_complete": 59
    },
    "preview": {
      "page_count": 24,
      "word_count": 14200,
      "detected_language": "en",
      "estimated_chunks": 148
    }
  }
}
```

**Job Stages:**
```
queued → downloading → parsing → cleaning → chunking → enriching → embedding → indexing → completed
                                                                                         ↕
                                                                                       failed
```

### 12.2 List Jobs

```http
GET /api/v1/ingestion-jobs?knowledge_base_id=kb_xyz789&status=failed&limit=50
```

### 12.3 Prometheus Metrics

| Metric | Description |
|--------|-------------|
| `ingestion_jobs_total` | Total jobs by status |
| `ingestion_job_duration_seconds` | Time from queue to completion |
| `ingestion_documents_processed_total` | Documents processed |
| `ingestion_chunks_created_total` | Total chunks indexed |
| `ingestion_tokens_embedded_total` | Tokens embedded (for cost tracking) |
| `ingestion_queue_depth` | Pending jobs in Celery queue |
| `ingestion_failures_total` | Failed jobs by error type |

---

## 13. Configuration Reference

```yaml
# config/ingestion.yaml

defaults:
  chunking:
    strategy: semantic
    chunk_size: 512
    chunk_overlap: 64
    min_chunk_size: 50
    max_chunk_size: 1024
    prepend_document_title: true
    prepend_section_heading: true

  embedding:
    provider: openai
    model: text-embedding-3-large
    dimensions: 1536
    batch_size: 100
    normalize: true

  metadata_enrichment:
    language_detection: true
    entity_extraction: false      # Enable for use cases needing entity filtering
    topic_classification: false
    auto_summary: false

  deduplication:
    document_level: true
    chunk_level: false            # Enable if knowledge base has many source overlaps

workers:
  concurrency: 8
  max_tasks_per_child: 100
  task_timeout_seconds: 1800     # 30 minutes
  retry_on_failure: true
  max_retries: 3
  retry_backoff_seconds: 60

storage:
  temp_dir: /tmp/neuralcore/ingestion
  max_file_size_mb: 500
  cleanup_temp_after_ingestion: true

pdf:
  parser: pymupdf
  extract_tables: true
  extract_images: false
  ocr_enabled: false

crawling:
  max_concurrent_requests: 5
  request_timeout_seconds: 30
  rate_limit_rps: 2
  respect_robots_txt: true
  max_page_size_mb: 10
```

---

## 14. Error Handling & Retries

### 14.1 Error Types

| Error Code | Cause | Retry |
|------------|-------|-------|
| `PARSE_FAILED` | Corrupted or unsupported file | No (manual review) |
| `FILE_TOO_LARGE` | Exceeds size limit | No |
| `DOWNLOAD_FAILED` | Network error fetching URL | Yes (3×) |
| `EMBEDDING_FAILED` | LLM provider API error | Yes (5×) |
| `INDEX_FAILED` | Qdrant unavailable | Yes (5×) |
| `QUOTA_EXCEEDED` | Provider token limit | No (upgrade plan) |
| `TIMEOUT` | Job exceeded time limit | Yes (1×) |

### 14.2 Failed Job Handling

```python
# List all failed jobs
failed_jobs = client.ingestion_jobs.list(
    kb_id="kb_xyz789",
    status="failed",
)

# Retry a failed job
for job in failed_jobs:
    print(f"{job.document_name}: {job.error_code} — {job.error_message}")
    if job.error_code == "DOWNLOAD_FAILED":
        client.ingestion_jobs.retry(job.id)
```

### 14.3 Dead Letter Queue

Jobs that fail all retries are moved to a dead-letter queue. Inspect and reprocess:

```http
GET /api/v1/ingestion-jobs?status=dead_lettered&kb_id=kb_xyz789

POST /api/v1/ingestion-jobs/{job_id}/retry
{ "force": true }
```

---

## 15. Performance & Scaling

### 15.1 Throughput Benchmarks

| Document Type | Avg Size | Parse Time | Chunk Time | Embed Time | Total |
|---------------|----------|-----------|------------|------------|-------|
| PDF (simple) | 500 KB | 0.5s | 0.2s | 2.1s | ~3s |
| PDF (scanned, OCR) | 2 MB | 45s | 0.5s | 4.2s | ~50s |
| DOCX | 200 KB | 0.2s | 0.1s | 1.8s | ~2s |
| HTML page | 50 KB | 0.1s | 0.05s | 0.9s | ~1s |
| CSV (1000 rows) | 100 KB | 0.3s | 0.1s | 3.5s | ~4s |

*Times measured with 8 Celery workers, OpenAI embedding API, text-embedding-3-large, 512-token chunks.*

### 15.2 Large-Scale Ingestion

For ingesting millions of documents:

```bash
# Scale workers horizontally
docker compose up -d --scale workers=16

# Use dedicated ingestion queue
celery -A workers.tasks worker --queues=ingestion --concurrency=16

# Monitor queue depth
watch 'redis-cli -a $REDIS_PASSWORD LLEN ingestion'
```

### 15.3 Cost Optimization

- Use `text-embedding-3-small` for large bulk ingestions (6× cheaper, ~97% quality)
- Enable chunk-level deduplication to avoid re-embedding unchanged content
- Use semantic chunking with larger chunks (512 tokens) — fewer chunks = lower cost
- Set `min_chunk_size: 100` to skip micro-chunks that add noise without value
- Use the async batch embedding API for >10,000 chunks (50% cheaper with OpenAI Batch API)

---

*For connector development, custom parser plugins, or enterprise-scale ingestion support, see [CONTRIBUTING.md](CONTRIBUTING.md) or open a GitHub issue tagged `area:ingestion`.*

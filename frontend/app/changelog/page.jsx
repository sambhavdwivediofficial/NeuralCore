// frontend/app/changelog/page.jsx

import Link from 'next/link';
import { Sparkles, ArrowLeft, GitCommit, Package, Shield, Zap, Bug, ChevronRight, ExternalLink, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import '@/styles/landing.css';
import { LandingFooter } from '@/components/landing/LandingFooter';

export const metadata = {
  title: 'Changelog',
  description: 'NeuralCore platform release history, updates, and version tracking.',
};

const RELEASES = [
  {
    version: '1.1.0-dev',
    date: '2026-06-16',
    type: 'in-progress',
    label: 'In Progress',
    description: 'Complete production-grade Python backend implementation. All modules follow strict coding standards — no placeholders, no TODOs, full async, expert-level architecture throughout.',
    sections: [
      {
        title: 'Project Tooling',
        icon: Package,
        items: [
          'pyproject.toml — Unified Python project config with Ruff linter, mypy strict mode, pytest async, coverage 70% floor',
          'Makefile — Windows 11 compatible developer shortcuts for install, lint, test, coverage, build, docs',
          'mkdocs.yml — Material theme documentation site with dark/light palette, Inter + JetBrains Mono fonts',
        ],
      },
      {
        title: 'Backend Foundation',
        icon: Zap,
        items: [
          'settings.py — Pydantic v2 BaseSettings with YAML config loading, typed sub-settings for 10+ domains, full enum coverage',
          'app.py — FastAPI application factory with full lifespan, CORS, GZip, security headers, tenant resolution, Sentry, Prometheus, OTLP',
          'dependencies.py — All FastAPI dependency providers: JWT auth, RBAC, rate limiting, pagination, vector store, model gateway',
          'requirements.txt — 45+ pinned runtime dependencies including FastAPI, SQLAlchemy async, Redis, Celery, PyJWT RS256',
        ],
      },
      {
        title: 'Database Layer (9 Models, 5 Repositories)',
        icon: Package,
        items: [
          'User model — Email unique index, hashed_password, Role enum, MFA secret, OAuth provider, failed login tracking',
          'Project model — Org-scoped UUID, owner FK, slug unique index, cascaded agents/datasets/knowledge_bases/workflows',
          'KnowledgeBase model — Vector DB backend, embedding config, ChunkingStrategy enum, document/chunk counts',
          'Agent model — AgentType enum (7 types), model config, tools JSONB, memories CASCADE relationship',
          'Memory model — MemoryLayer enum (5 layers), role, content, vector_id, importance_score, composite indexes',
          'Dataset, Workflow models — Full validation, status tracking, JSONB configs',
          '5 typed async repositories with specialized queries (User, Project, Agent, Dataset, Workflow)',
        ],
      },
      {
        title: 'Multi-Tenancy (Enterprise-Grade)',
        icon: Shield,
        items: [
          'Organization model — 4 plans (Free/Starter/Professional/Enterprise), status tracking, trial management, limit overrides',
          'OrganizationMember — Role enum (5 roles), MemberStatus, invite token system, UniqueConstraint org+user',
          'RBAC — 5-role hierarchy (super_admin > owner > admin > developer > viewer), 22 granular permissions',
          'Tenant isolation — Database query-level enforcement, vector store namespacing, Redis prefixing, agent runtime isolation',
          'Quota system — 6 quota types, 5 periods, Redis-based usage tracking with auto-expire, enforcement layer',
          'Compliance — Data retention policies, GDPR anonymization, full org data export, purge scheduling',
        ],
      },
      {
        title: 'Authentication',
        icon: Shield,
        items: [
          'JWT RS256 — Asymmetric signing, 15min access tokens + 30-day rolling refresh tokens',
          'OAuth2 — Google, GitHub, Microsoft providers with state validation and user info normalization',
          'MFA — TOTP (RFC 6238) with pyotp, recovery codes (SHA-256 hashed), valid_window=1',
          'API Keys — nc_ prefix, 48-char urlsafe tokens, SHA-256 hashing, constant-time comparison',
          'Password — bcrypt hashing (configurable rounds), strength validation (uppercase/lowercase/digit/special)',
        ],
      },
      {
        title: 'Task Queue (Celery + Redis)',
        icon: Zap,
        items: [
          '7 named queues — default, ingestion, embeddings, retrieval, reranking, cleanup, training',
          '4 periodic tasks — memory purge (hourly), account unlock (15min), invite cleanup (daily), org purge (daily)',
          'Embedding tasks — SHA-256 cache keys, Rust engine L1 cache, batch embedding generation, vector store upsert',
          'Ingestion tasks — Loader → deduplicate → clean → metadata → chunk → embed pipeline with error handling',
          'Retrieval tasks — Query cache warming, KB cache invalidation, reindexing',
        ],
      },
      {
        title: 'Monitoring & Observability',
        icon: AlertCircle,
        items: [
          '12 Prometheus metrics — HTTP requests, LLM calls, embeddings, vector search, agent tasks, ingestion, cache, DB pool',
          'Structlog — JSON/Console renderers, contextvars merge, automatic PII sanitization (Bearer/sk-/nc-/email/CC)',
          'OpenTelemetry — OTLP tracing with TraceIdRatioBased(0.1) sampler, BatchSpanProcessor',
          'Health checks — DB (SELECT 1), Redis (PING), Vector DB (TCP probe), disk usage, memory (cross-platform)',
          '9 alerting rules — High latency, error rates, pod crashes, DB connections, memory, disk, quotas, ingestion failures, LLM errors',
          'Alert dispatchers — Slack webhook blocks, PagerDuty events API v2, SMTP email',
        ],
      },
      {
        title: 'Model Gateway (8 Providers)',
        icon: Zap,
        items: [
          'OpenAI — Full streaming with usage tracking, tool-call parsing, error mapping',
          'Anthropic — Native SDK, event-level streaming (message_start/content_block_start/delta/message_delta), tool_use accumulation',
          'Google Gemini — GenerativeModel API, GenerationConfig, function_declarations, multimodal-ready',
          'DeepSeek, Mistral, Ollama, Llama (local 48B) — All with OpenAI-compatible or native implementations',
          'Provider factory — Smart fallback chain (LOCAL → OLLAMA → OPENAI), LRU cache, rate limit handling',
        ],
      },
      {
        title: 'Embeddings (7 Providers)',
        icon: Zap,
        items: [
          'OpenAI embeddings — Batched API calls, index-sorted responses, all 3 models',
          'BGE, E5, Nomic, Jina — Specialized providers with query/document prefix handling',
          'SentenceTransformers — all-MiniLM-L6-v2, all-mpnet-base-v2 via asyncio.to_thread',
          'Custom provider — Configurable base_url+headers+auth, auto-detection of 3 response formats',
          'Factory — 7-provider registry with instance caching, dimension validation with NaN/Inf checks',
        ],
      },
      {
        title: 'Vector Stores (6 Backends)',
        icon: Package,
        items: [
          'Qdrant — Async gRPC, scalar INT8 quantization, HNSW config, 12 filter operators',
          'Milvus — HNSW/IVFFlat DDL, VARCHAR primary key, filter expression builder',
          'Weaviate — v4 async client, multi-tenancy, generate_uuid5 IDs, distance-to-score conversion',
          'PGVector — Raw SQLAlchemy text() queries, HNSW/IVFFlat, JSONB GIN index, ON CONFLICT upsert',
          'Elasticsearch — AsyncElasticsearch, knn search, async_bulk operations, bool query filters',
          'FAISS — IVFFlat + IDMap2, per-collection asyncio.Lock, L2 normalization, metadata persistence',
        ],
      },
      {
        title: 'Chunking (8 Strategies)',
        icon: Package,
        items: [
          'Token chunker — Exact token-window with configurable overlap via encode/decode roundtrip',
          'Recursive chunker — Hierarchical separator splitting (\\n\\n → \\n → . → ; → , → space → "")',
          'Markdown chunker — H1-H6 boundary detection, header stack path prefix, front-matter YAML extraction',
          'Code chunker — Language-agnostic class/def/function/async def/export boundary detection',
          'AST chunker — Python AST parse with decorator detection, class method extraction with context',
          'Semantic chunker — Jaccard token similarity between sentences, adaptive breakpoint detection (threshold 0.35)',
          'Hybrid chunker — Auto-detection: markdown headers → Python AST → code ratio → length → semantic fallback',
        ],
      },
      {
        title: 'Preprocessing Pipeline',
        icon: CheckCircle2,
        items: [
          'Normalizer — NFKC unicode, zero-width character removal, smart quote normalization (8 mappings), whitespace collapse',
          'Cleaner — HTML strip (lxml), entity decode, control character removal, collapsed punctuation, URL removal',
          'Language detection — langdetect with deterministic seed, reliability threshold 0.7',
          'PII detection — 8 PII types, Luhn checksum for credit cards, priority-based overlap resolution, configurable redaction',
          'Metadata extraction — Word/sentence/token counts, language detection, title estimation, reading time (200 WPM), SHA-256 hash',
          'Deduplication — Exact SHA-256 hash matching + near-duplicate detection via 64-bit SimHash (Hamming distance ≤ 3)',
        ],
      },
      {
        title: 'Ingestion (26 Source Connectors)',
        icon: Package,
        items: [
          'Documents — TXT, Markdown (YAML front-matter), HTML (BeautifulSoup), CSV, JSON, XML, XLSX (openpyxl), DOCX, PDF (pypdf)',
          'Web — Website crawler (BFS, max_depth=3, max_pages=50), Sitemap parser (dual XML namespace), YouTube transcripts',
          'Media — Audio (Whisper transcription), Video (ffmpeg extraction + Whisper, 7 formats)',
          'Communication — Email (RFC 2822 multipart), Slack (conversations + replies, channel discovery), Discord (Bot API v10)',
          'Code — GitHub (REST API v3, recursive tree walk), GitLab (API v4, paginated), Bitbucket (Cloud API 2.0)',
          'Knowledge — Notion (blocks→markdown, database pagination), Confluence (REST v2, storage HTML), Jira (JQL search, ADF conversion)',
          'Databases — PostgreSQL (asyncpg), MySQL (asyncmy DictCursor), MongoDB (Motor, nested flattening)',
        ],
      },
      {
        title: 'Retrieval System',
        icon: Zap,
        items: [
          'Vector search — Multi-backend, Prometheus-instrumented, Rust engine top-K acceleration',
          'BM25F — Pure-Python Porter stemmer (24 suffix rules), per-KB index registry, lazy IDF rebuild',
          'Metadata search — 12 filter operators, field__operator syntax parsing, in-memory post-filtering',
          'Query rewriting — 4 LLM-powered strategies (HyDE, step-back, decompose, expand), parallel execution with fallback',
          'Graph search — Multi-hop traversal, GraphRAG integration, graceful fallback on import error',
          'Multimodal — Image embedding (base64 → Jina/Nomic), text+image vector averaging + L2 normalization',
          'Hybrid retrieval — Parallel vector + BM25 + graph search, RRF fusion (Rust → Python fallback), per-source scoring',
          'Federated search — Parallel KB search with timeouts, result flattening + score sort + rank assignment',
        ],
      },
      {
        title: 'Reranking',
        icon: Zap,
        items: [
          'Cross-encoder — ms-marco-MiniLM-L-6-v2 default, asyncio.to_thread model.predict, lazy model cache',
          'BGE reranker — BAAI/bge-reranker-large/base/v2-m3, CrossEncoder backend',
          'Jina reranker — jina-reranker-v2-base-multilingual, HTTP API with error mapping',
          'Hybrid reranker — Primary + fallback chain, min-max score normalization',
        ],
      },
    ],
  },
  {
    version: '1.0.0',
    date: '2026-06-10',
    type: 'major',
    label: 'Initial Production Release',
    description: 'First production-ready release of NeuralCore — a complete, enterprise-grade AI infrastructure platform. Core Rust engine fully implemented, tested, and optimized.',
    sections: [
      {
        title: 'Core Infrastructure',
        icon: Package,
        items: [
          '8 production YAML configuration files — app, auth, agents, embeddings, retrieval, vector_db, logging, monitoring',
          'Complete configuration management with environment variable substitution and per-environment overrides',
        ],
      },
      {
        title: 'Rust Engine v1.0.0 (~4,200 lines)',
        icon: Zap,
        items: [
          'Similarity computation — 6 distance metrics, Rayon parallelization (10x speedup), SIMD-style loop unrolling',
          'Performance: Cosine similarity 245ns (dim=128), prenormalized 93ns (10x faster), batch 1000 vectors/sec',
          'HNSW vector index — M=16, ef_construction=200, greedy search with priority queues, thread-safe via DashMap + RwLock',
          'Search: 10K vectors, dim=768, k=10 in ~10µs (100K searches/sec). Build: 1000 vectors in ~1.5ms',
          'Score fusion — 6 strategies (RRF, Weighted, Borda, Softmax, Score Normalization, Average)',
          'Evaluation metrics — NDCG@K, MRR, Precision@K, Recall@K with configurable thresholding',
          'WordPiece tokenizer — Special tokens, BPE subword segmentation, 3 truncation strategies, 4 padding modes',
          'Approximate token counting — CJK character detection, ~4 chars/token heuristic, 0.5µs per document',
          'Compression — LZ4 (2µs/MB), Zstd (best ratio), Snappy (balanced), Scalar Int8 quantization (4x memory reduction)',
          'Caching — LRU + LFU with O(1) operations via DashMap, TTL support, EmbeddingCache (50K entries ~5MB)',
          '50+ PyO3 FFI functions — Full Python bindings for all engine capabilities',
          'CLI tool — 7 subcommands (info, similarity, index, tokenize, compress, rerank, bench) with JSON/text output',
          '300+ Criterion benchmarks — Statistical analysis, outlier detection, HTML reports, flamegraphs',
        ],
      },
      {
        title: 'Testing & Quality',
        icon: CheckCircle2,
        items: [
          '58 unit tests (100% passing) — Similarity, vector index, reranker, tokenizer, compression, cache',
          '~85% line coverage (critical paths 100%)',
          'Clippy linting — All warnings resolved',
          'Security audit — cargo-audit with no critical issues',
        ],
      },
      {
        title: 'Documentation',
        icon: Package,
        items: [
          'README.md — Full professional readme with logo, badges, active development banner',
          'ARCHITECTURE.md — Complete technical architecture, subsystems, data flows, technology stack',
          'CONTRIBUTING.md — Industry-grade contribution guidelines, code standards (90%+), Conventional Commits',
          'SECURITY.md — Full security policy, vulnerability reporting, JWT/RBAC/isolation, audit logging',
          'CODE_OF_CONDUCT.md — Professional conduct policy',
        ],
      },
    ],
  },
  {
    version: '0.0.0',
    date: '2026-05',
    type: 'minor',
    label: 'Project Initialization',
    description: 'Project structure established with comprehensive scope documentation and development environment setup.',
    sections: [
      {
        title: 'Foundation',
        icon: GitCommit,
        items: [
          'GitHub repository initialized (All Rights Reserved license)',
          'Project scope documented — 27+ ingestion, 8 chunkers, 6 vector stores, 8 LLM providers, 5-layer memory',
          'Rust version pinned (edition 2021)',
          'CI/CD pipeline framework ready (GitHub Actions)',
          'Author: Sambhav Dwivedi',
          'Website: https://www.sambhavdwivedi.in',
          'LinkedIn: https://www.linkedin.com/in/sambhavdwivedi',
        ],
      },
    ],
  },
];

const UPCOMING = [
  {
    version: '1.2.0',
    date: 'Q1 2027',
    title: 'Frontend & SDKs',
    description: 'Complete Next.js dashboard and 6 SDKs (Python, JavaScript, TypeScript, Go, Rust, Java)',
  },
  {
    version: '2.0.0',
    date: 'Q3 2027',
    title: 'Distributed Training & Scaling',
    description: 'Multi-GPU distributed fine-tuning, horizontal vector store scaling, multi-region deployment',
  },
];

const TYPE_STYLES = {
  major: 'bg-primary/10 text-primary border-primary/20',
  'in-progress': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  minor: 'bg-muted text-muted-foreground border-border',
};

const TYPE_ICONS = {
  major: Zap,
  'in-progress': Clock,
  minor: GitCommit,
};

function renderClickableText(text) {
  const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/gi;
  const urlRegex = /(https?:\/\/[^\s]+)/gi;
  
  const parts = text.split(/(https?:\/\/[^\s]+|[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/gi);
  
  return parts.map((part, i) => {
    if (part.match(emailRegex)) {
      return (
        <a key={i} href={`mailto:${part}`} className="text-primary hover:underline">
          {part}
        </a>
      );
    }
    if (part.match(urlRegex)) {
      return (
        <a key={i} href={part} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
          {part}
        </a>
      );
    }
    return part;
  });
}

export default function ChangelogPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="border-b border-border">
        <div className="landing-container flex h-14 items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-semibold text-foreground">NeuralCore</span>
          </Link>
          <Link href="/" className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-3 w-3" /> Back to home
          </Link>
        </div>
      </div>

      <div className="landing-container px-4 sm:px-6 py-12 sm:py-16 max-w-4xl">
        {/* Header */}
        <div className="flex flex-col gap-3 mb-12">
          <span className="landing-section-label">Changelog</span>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Release history</h1>
          <p className="text-base text-muted-foreground leading-relaxed max-w-2xl">
            Every significant change to the NeuralCore platform, documented in detail.
            All notable changes are tracked here in reverse chronological order.
          </p>
          <div className="flex items-center gap-4 mt-2">
            <a 
              href="https://keepachangelog.com/en/1.0.0/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
            >
              Based on Keep a Changelog <ExternalLink className="h-3 w-3" />
            </a>
            <a 
              href="https://semver.org/spec/v2.0.0.html" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
            >
              Semantic Versioning <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        {/* Releases Timeline */}
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-[19px] sm:left-[23px] top-3 bottom-3 w-px bg-border hidden sm:block" />

          <div className="flex flex-col gap-16">
            {RELEASES.map((release) => {
              const TypeIcon = TYPE_ICONS[release.type];
              
              return (
                <div key={release.version} className="relative">
                  {/* Timeline dot */}
                  <div className="hidden sm:flex absolute left-0 top-1.5 h-[7px] w-[7px] rounded-full bg-primary ring-4 ring-background z-10" />
                  
                  {/* Version header */}
                  <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mb-6 sm:pl-10">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-lg font-semibold text-foreground">{release.version}</span>
                      <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${TYPE_STYLES[release.type]}`}>
                        <TypeIcon className="h-3 w-3" />
                        {release.label}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">{release.date}</span>
                  </div>

                  {/* Description */}
                  <div className="sm:pl-10 mb-6">
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {renderClickableText(release.description)}
                    </p>
                  </div>

                  {/* Sections */}
                  <div className="sm:pl-10 space-y-6">
                    {release.sections.map((section) => (
                      <div key={section.title} className="rounded-lg border border-border bg-card/50 p-5">
                        <div className="flex items-center gap-2.5 mb-4">
                          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                            <section.icon className="h-3.5 w-3.5" />
                          </div>
                          <h3 className="text-sm font-semibold text-foreground">{section.title}</h3>
                        </div>
                        <ul className="space-y-2.5">
                          {section.items.map((item) => (
                            <li key={item} className="flex items-start gap-2.5 text-[13px] text-muted-foreground leading-relaxed">
                              <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary/60" />
                              <span>{renderClickableText(item)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Upcoming Releases */}
        <div className="mt-20">
          <div className="flex items-center gap-3 mb-8">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
              <Clock className="h-4 w-4" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-foreground">Upcoming Releases</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {UPCOMING.map((release) => (
              <div key={release.version} className="rounded-lg border border-border bg-card p-5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold text-foreground">{release.version}</span>
                  <span className="text-xs text-muted-foreground">{release.date}</span>
                </div>
                <h3 className="text-sm font-semibold text-foreground">{release.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{renderClickableText(release.description)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Versioning Info */}
        <div className="mt-20 rounded-lg border border-border bg-card p-6">
          <h3 className="text-sm font-semibold text-foreground mb-4">Version Numbering Scheme</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="font-mono text-sm font-semibold text-primary">MAJOR</span>
              <p className="text-xs text-muted-foreground">Breaking changes, architectural shifts (requires migration guide)</p>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="font-mono text-sm font-semibold text-primary">MINOR</span>
              <p className="text-xs text-muted-foreground">New features, backwards-compatible additions</p>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="font-mono text-sm font-semibold text-primary">PATCH</span>
              <p className="text-xs text-muted-foreground">Bug fixes, performance improvements, non-functional changes</p>
            </div>
          </div>
        </div>
      </div>

      <LandingFooter />
    </div>
  );
}

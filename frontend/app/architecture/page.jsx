// frontend/app/architecture/page.jsx

import Link from 'next/link';
import { Sparkles, ArrowLeft, ArrowRight } from 'lucide-react';
import '@/styles/landing.css';
import { LandingFooter } from '@/components/landing/LandingFooter';
import { ROUTES } from '@/lib/routes';

export const metadata = {
  title: 'Architecture',
  description: 'NeuralCore platform architecture — subsystems, data flows, and design principles.',
};

const PRINCIPLES = [
  {
    title: 'Strict Modularity',
    desc: 'Every subsystem is an independent module. Domain boundaries are enforced at the code level. Subsystems communicate through defined interfaces, not internal references — independently testable, replaceable, and deployable.',
  },
  {
    title: 'Provider Agnosticism',
    desc: 'No part of the core platform is tied to a specific model provider, vector store, embedding model, or payment processor. All external integrations are accessed through abstraction layers. Switching providers is a configuration operation, not a code change.',
  },
  {
    title: 'Async-First Design',
    desc: 'The entire backend is built on asynchronous Python with FastAPI and async SQLAlchemy. Every I/O-bound operation is non-blocking — database access, vector store queries, model API calls, background task execution.',
  },
  {
    title: 'Tenant Isolation by Default',
    desc: 'Multi-tenancy is a foundational constraint. Every data access path enforces tenant context. There is no code path that can return cross-tenant data through correct usage.',
  },
  {
    title: 'Performance at the Boundary',
    desc: 'Python handles orchestration and business logic. Rust handles computation — HNSW indexing, SIMD similarity, cross-encoder reranking, tokenization, LRU/LFU caching — all via PyO3 FFI with no serialization overhead.',
  },
  {
    title: 'Observability as Infrastructure',
    desc: 'Logging, distributed tracing, metrics collection, and alerting are built into the platform at the middleware and service layers. Every request is traced. Every significant operation is logged. Every subsystem exposes metrics.',
  },
];

const LAYERS = [
  {
    name: 'Client Layer',
    color: 'border-blue-500/30 bg-blue-500/5',
    dotColor: 'bg-blue-500',
    items: ['Web UI (Next.js 14)', 'Python SDK', 'TypeScript SDK', 'REST API'],
  },
  {
    name: 'API Gateway',
    color: 'border-violet-500/30 bg-violet-500/5',
    dotColor: 'bg-violet-500',
    items: ['FastAPI Router', 'JWT Middleware', 'Tenant Resolver', 'Rate Limiter'],
  },
  {
    name: 'RAG Pipeline',
    color: 'border-emerald-500/30 bg-emerald-500/5',
    dotColor: 'bg-emerald-500',
    items: ['Ingestion (27+ sources)', 'Chunking (8 strategies)', 'Embedding (8 providers)', 'Retrieval (7 modes)', 'Reranking', 'Prompt Engine'],
  },
  {
    name: 'Agent System',
    color: 'border-orange-500/30 bg-orange-500/5',
    dotColor: 'bg-orange-500',
    items: ['Agent Runtime', 'A2A Protocol', '5-Layer Memory', 'Tool Framework', 'Workflow Engine', 'MCP Layer'],
  },
  {
    name: 'Core Services',
    color: 'border-pink-500/30 bg-pink-500/5',
    dotColor: 'bg-pink-500',
    items: ['Model Gateway', 'Vector Store Abstraction', 'Knowledge Graph', 'Background Queue (Celery)', 'Rust Engine (PyO3)'],
  },
  {
    name: 'Data Layer',
    color: 'border-cyan-500/30 bg-cyan-500/5',
    dotColor: 'bg-cyan-500',
    items: ['PostgreSQL 16', 'Redis 7', 'Qdrant / Milvus / Weaviate', 'PGVector / Elasticsearch / FAISS', 'S3-compatible Object Storage'],
  },
];

const PERFORMANCE = [
  { metric: 'Cosine similarity (dim=1536)', value: '6.2μs', sub: '~160K ops/sec' },
  { metric: 'Prenormalized cosine (dim=1536)', value: '0.48μs', sub: '~2M ops/sec — 13× faster' },
  { metric: 'HNSW search (10K vectors, k=10)', value: '~10μs', sub: '100K searches/sec' },
  { metric: 'Cross-encoder reranking (top-20)', value: '<10ms', sub: 'ONNX Runtime via Rust' },
  { metric: 'RRF fusion (100 items × 2 lists)', value: '25μs', sub: 'Rust reranker.rs' },
  { metric: 'Token count approximate', value: '0.5μs', sub: '2K docs/sec batch' },
  { metric: 'Embedding cache get/set', value: '<1μs', sub: '50K entry / ~5MB memory' },
  { metric: 'HNSW build (1K vectors, dim=1536)', value: '~1.5ms', sub: '~64 bytes/vector overhead' },
];

export default function ArchitecturePage() {
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

      <div className="landing-container px-4 sm:px-6 py-12 sm:py-16 max-w-5xl">
        <div className="flex flex-col gap-3 mb-14">
          <span className="landing-section-label">Architecture</span>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            How NeuralCore is built
          </h1>
          <p className="text-base text-muted-foreground leading-relaxed max-w-2xl">
            A modular, provider-agnostic, multi-tenant AI infrastructure platform.
            Every subsystem is independently replaceable. No vendor lock-in at any layer.
          </p>
        </div>

        <div className="flex flex-col gap-12">
          <div>
            <h2 className="text-lg font-semibold text-foreground mb-6">Core Design Principles</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {PRINCIPLES.map((p) => (
                <div key={p.title} className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
                  <h3 className="text-sm font-semibold text-foreground">{p.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{p.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground mb-6">Platform Layers</h2>
            <div className="flex flex-col gap-3">
              {LAYERS.map((layer) => (
                <div key={layer.name} className={`rounded-lg border p-4 ${layer.color}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`h-2 w-2 rounded-full ${layer.dotColor}`} />
                    <span className="text-xs font-semibold uppercase tracking-wider text-foreground">{layer.name}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {layer.items.map((item) => (
                      <span key={item} className="rounded-md border border-border bg-background/60 px-2.5 py-1 text-xs text-muted-foreground">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-foreground mb-2">Rust Engine Benchmarks</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Measured on a single core. All times are for the Rust implementation via PyO3 FFI — not Python.
            </p>
            <div className="rounded-lg border border-border overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40">
                    <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Operation</th>
                    <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Latency</th>
                    <th className="px-4 py-2.5 text-right font-medium text-muted-foreground hidden sm:table-cell">Note</th>
                  </tr>
                </thead>
                <tbody>
                  {PERFORMANCE.map((row, i) => (
                    <tr key={row.metric} className={`border-b border-border last:border-0 ${i % 2 === 0 ? '' : 'bg-muted/20'}`}>
                      <td className="px-4 py-2.5 text-muted-foreground font-mono">{row.metric}</td>
                      <td className="px-4 py-2.5 text-right text-foreground font-semibold font-mono">{row.value}</td>
                      <td className="px-4 py-2.5 text-right text-muted-foreground hidden sm:table-cell">{row.sub}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              href={ROUTES.SIGNUP}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
            >
              Start building <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="http://localhost:8000/api/v1/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
            >
              API Reference
            </a>
          </div>
        </div>
      </div>

      <LandingFooter />
    </div>
  );
}

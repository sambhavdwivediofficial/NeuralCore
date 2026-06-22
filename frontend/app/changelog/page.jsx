// frontend/app/changelog/page.jsx

import Link from 'next/link';
import { Sparkles, ArrowLeft } from 'lucide-react';
import '@/styles/landing.css';
import { LandingFooter } from '@/components/landing/LandingFooter';

export const metadata = {
  title: 'Changelog — NeuralCore',
  description: 'NeuralCore platform release history and updates.',
};

const RELEASES = [
  {
    version: 'v1.0.0',
    date: 'June 2026',
    type: 'major',
    label: 'Initial Release',
    highlights: [
      'Complete Rust performance engine — HNSW indexing, SIMD cosine similarity, BGE reranking acceleration, tokenization, LRU/LFU caching via PyO3 FFI (58 tests passing)',
      'Production RAG pipeline — hybrid vector + BM25 with RRF fusion, HyDE/step-back/decomposition query rewriting, cross-encoder reranking',
      'Multi-agent runtime — 7 agent types, A2A protocol, checkpointing, lifecycle management, SSE streaming',
      '5-layer memory system — short-term (Redis), long-term (Postgres), semantic (vector), episodic, session',
      'GraphRAG — entity extraction, relationship scoring, cross-document resolution, multi-hop traversal',
      '6 vector store backends — Qdrant, Milvus, Weaviate, PGVector, Elasticsearch, FAISS unified abstraction',
      '8 LLM providers — OpenAI, Anthropic, Google Gemini, DeepSeek, Mistral, Llama, Ollama, local 48B model',
      '27+ data source connectors — PDF, DOCX, GitHub, Notion, Confluence, Slack, Jira, databases, YouTube',
      'Enterprise multi-tenancy — full isolation at DB, vector, cache, agent layers with RBAC',
      'LoRA/QLoRA fine-tuning pipeline with job queue, progress streaming, model registry',
      'Complete Kubernetes, Docker, Terraform infrastructure — production-ready',
      'Prometheus + Grafana + Loki + OpenTelemetry observability stack',
      'MCP (Model Context Protocol) server and client support',
      'Billing system — Stripe, Razorpay, PayPal with usage metering',
    ],
  },
  {
    version: 'v1.1.0',
    date: 'Coming soon',
    type: 'upcoming',
    label: 'Backend Completion',
    highlights: [
      'All FastAPI route layers fully wired end-to-end',
      'Celery background workers for ingestion, embedding, reranking',
      'Signup, invite accept, OAuth, MFA challenge backend endpoints',
      'Billing routes exposed (Stripe webhooks, invoice generation)',
      'Fine-tuning and evaluation API routes live',
      'Usage metering write-side fully connected',
    ],
  },
  {
    version: 'v1.2.0',
    date: 'Q3 2026',
    type: 'upcoming',
    label: 'Frontend & SDKs',
    highlights: [
      'Complete Next.js dashboard — all pages production-ready',
      'Python, TypeScript, JavaScript, Go, Rust, Java SDKs',
      'Real-time agent execution visualization',
      'Embedding scatter plot explorer',
      'Retrieval debugger with GraphRAG visualization',
    ],
  },
  {
    version: 'v2.0.0',
    date: 'Q4 2026',
    type: 'upcoming',
    label: 'Distributed Training & Multimodal',
    highlights: [
      'DDP / FSDP / DeepSpeed distributed training infrastructure',
      'Native multimodal reasoning — text + image + audio',
      'Autonomous agent networks with federated knowledge',
      'Real-time streaming retrieval',
      'AI operating system primitives',
    ],
  },
];

const TYPE_STYLES = {
  major: 'bg-primary/10 text-primary border-primary/20',
  upcoming: 'bg-muted text-muted-foreground border-border',
};

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

      <div className="landing-container px-4 sm:px-6 py-12 sm:py-16 max-w-3xl">
        <div className="flex flex-col gap-2 mb-12">
          <span className="landing-section-label">Changelog</span>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Release history</h1>
          <p className="text-sm text-muted-foreground">
            Every significant change to the NeuralCore platform, documented.
          </p>
        </div>

        <div className="flex flex-col gap-10">
          {RELEASES.map((release) => (
            <div key={release.version} className="flex flex-col sm:flex-row gap-5">
              <div className="flex flex-col items-start gap-1.5 sm:w-32 flex-shrink-0">
                <span className="font-mono text-sm font-semibold text-foreground">{release.version}</span>
                <span className="text-xs text-muted-foreground">{release.date}</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${TYPE_STYLES[release.type]}`}>
                  {release.label}
                </span>
              </div>

              <div className="flex-1 rounded-lg border border-border bg-card p-5">
                <ul className="flex flex-col gap-2.5">
                  {release.highlights.map((item) => (
                    <li key={item} className="flex items-start gap-2.5 text-xs text-muted-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>

      <LandingFooter />
    </div>
  );
}

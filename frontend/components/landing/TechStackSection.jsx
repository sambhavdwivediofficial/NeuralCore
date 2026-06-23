'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const ROW_1 = [
  { name: 'OpenAI', color: '#10a37f', cat: 'LLM' },
  { name: 'Anthropic', color: '#c96442', cat: 'LLM' },
  { name: 'Google Gemini', color: '#4285f4', cat: 'LLM' },
  { name: 'Ollama', color: '#e5e5e5', cat: 'LLM' },
  { name: 'Mistral', color: '#f7931e', cat: 'LLM' },
  { name: 'DeepSeek', color: '#4c6ef5', cat: 'LLM' },
  { name: 'Llama', color: '#7c3aed', cat: 'LLM' },
  { name: 'Qdrant', color: '#dc244c', cat: 'Vector' },
  { name: 'Milvus', color: '#00b5d8', cat: 'Vector' },
  { name: 'Weaviate', color: '#fa0050', cat: 'Vector' },
  { name: 'PGVector', color: '#336791', cat: 'Vector' },
  { name: 'Elasticsearch', color: '#f4bd19', cat: 'Vector' },
  { name: 'FAISS', color: '#0467df', cat: 'Vector' },
  { name: 'OpenAI', color: '#10a37f', cat: 'LLM' },
  { name: 'Anthropic', color: '#c96442', cat: 'LLM' },
  { name: 'Google Gemini', color: '#4285f4', cat: 'LLM' },
  { name: 'Ollama', color: '#e5e5e5', cat: 'LLM' },
  { name: 'Mistral', color: '#f7931e', cat: 'LLM' },
  { name: 'DeepSeek', color: '#4c6ef5', cat: 'LLM' },
  { name: 'Llama', color: '#7c3aed', cat: 'LLM' },
  { name: 'Qdrant', color: '#dc244c', cat: 'Vector' },
  { name: 'Milvus', color: '#00b5d8', cat: 'Vector' },
  { name: 'Weaviate', color: '#fa0050', cat: 'Vector' },
  { name: 'PGVector', color: '#336791', cat: 'Vector' },
  { name: 'Elasticsearch', color: '#f4bd19', cat: 'Vector' },
  { name: 'FAISS', color: '#0467df', cat: 'Vector' },
];

const ROW_2 = [
  { name: 'FastAPI', color: '#05998b', cat: 'Backend' },
  { name: 'PostgreSQL', color: '#336791', cat: 'DB' },
  { name: 'Redis', color: '#dc382d', cat: 'Cache' },
  { name: 'Celery', color: '#37814a', cat: 'Queue' },
  { name: 'Rust', color: '#ce412b', cat: 'Engine' },
  { name: 'PyO3', color: '#e4d031', cat: 'FFI' },
  { name: 'Stripe', color: '#6772e5', cat: 'Billing' },
  { name: 'Razorpay', color: '#3395ff', cat: 'Billing' },
  { name: 'Prometheus', color: '#e6522c', cat: 'Metrics' },
  { name: 'Grafana', color: '#f46800', cat: 'Monitor' },
  { name: 'OpenTelemetry', color: '#f5a800', cat: 'Tracing' },
  { name: 'Kubernetes', color: '#326ce5', cat: 'Infra' },
  { name: 'FastAPI', color: '#05998b', cat: 'Backend' },
  { name: 'PostgreSQL', color: '#336791', cat: 'DB' },
  { name: 'Redis', color: '#dc382d', cat: 'Cache' },
  { name: 'Celery', color: '#37814a', cat: 'Queue' },
  { name: 'Rust', color: '#ce412b', cat: 'Engine' },
  { name: 'PyO3', color: '#e4d031', cat: 'FFI' },
  { name: 'Stripe', color: '#6772e5', cat: 'Billing' },
  { name: 'Razorpay', color: '#3395ff', cat: 'Billing' },
  { name: 'Prometheus', color: '#e6522c', cat: 'Metrics' },
  { name: 'Grafana', color: '#f46800', cat: 'Monitor' },
  { name: 'OpenTelemetry', color: '#f5a800', cat: 'Tracing' },
  { name: 'Kubernetes', color: '#326ce5', cat: 'Infra' },
];

const ROW_3 = [
  { name: 'BGE Reranker', color: '#8b5cf6', cat: 'Rerank' },
  { name: 'Jina', color: '#10a37f', cat: 'Embed' },
  { name: 'Nomic', color: '#f59e0b', cat: 'Embed' },
  { name: 'Sentence Transformers', color: '#ec4899', cat: 'Embed' },
  { name: 'GitHub', color: '#e5e5e5', cat: 'Source' },
  { name: 'Notion', color: '#e5e5e5', cat: 'Source' },
  { name: 'Confluence', color: '#0052cc', cat: 'Source' },
  { name: 'Slack', color: '#611f69', cat: 'Source' },
  { name: 'Jira', color: '#0052cc', cat: 'Source' },
  { name: 'Docker', color: '#2496ed', cat: 'Deploy' },
  { name: 'Terraform', color: '#7b42bc', cat: 'IaC' },
  { name: 'Next.js', color: '#e5e5e5', cat: 'Frontend' },
  { name: 'BGE Reranker', color: '#8b5cf6', cat: 'Rerank' },
  { name: 'Jina', color: '#10a37f', cat: 'Embed' },
  { name: 'Nomic', color: '#f59e0b', cat: 'Embed' },
  { name: 'Sentence Transformers', color: '#ec4899', cat: 'Embed' },
  { name: 'GitHub', color: '#e5e5e5', cat: 'Source' },
  { name: 'Notion', color: '#e5e5e5', cat: 'Source' },
  { name: 'Confluence', color: '#0052cc', cat: 'Source' },
  { name: 'Slack', color: '#611f69', cat: 'Source' },
  { name: 'Jira', color: '#0052cc', cat: 'Source' },
  { name: 'Docker', color: '#2496ed', cat: 'Deploy' },
  { name: 'Terraform', color: '#7b42bc', cat: 'IaC' },
  { name: 'Next.js', color: '#e5e5e5', cat: 'Frontend' },
];

function MarqueeRow({ items, reverse = false, duration = 40 }) {
  const half = items.length / 2;
  const firstHalf = items.slice(0, half);

  return (
    <div className="relative flex overflow-hidden">
      <div
        className="pointer-events-none absolute inset-y-0 left-0 z-10 w-32"
        style={{ background: 'linear-gradient(to right, hsl(var(--background)), transparent)' }}
      />
      <div
        className="pointer-events-none absolute inset-y-0 right-0 z-10 w-32"
        style={{ background: 'linear-gradient(to left, hsl(var(--background)), transparent)' }}
      />

      <motion.div
        animate={reverse
          ? { x: ['-50%', '0%'] }
          : { x: ['0%', '-50%'] }
        }
        transition={{
          duration,
          repeat: Infinity,
          ease: 'linear',
          repeatType: 'loop',
        }}
        className="flex gap-3 flex-shrink-0 py-1.5"
        style={{ willChange: 'transform' }}
      >
        {items.map((item, i) => (
          <div
            key={i}
            className="flex items-center gap-2.5 rounded-lg border border-border bg-card px-4 py-2.5 flex-shrink-0 cursor-default select-none"
            style={{ minWidth: 'max-content' }}
          >
            <div
              className="h-2 w-2 rounded-full flex-shrink-0"
              style={{
                backgroundColor: item.color,
                boxShadow: `0 0 8px ${item.color}70`,
              }}
            />
            <span className="text-[0.8125rem] font-medium text-foreground">{item.name}</span>
            <span
              className="text-[0.625rem] font-semibold tracking-wider uppercase"
              style={{ color: 'hsl(var(--muted-foreground) / 0.5)' }}
            >
              {item.cat}
            </span>
          </div>
        ))}
      </motion.div>
    </div>
  );
}

const COUNTS = [
  { count: '8', label: 'LLM Providers' },
  { count: '6', label: 'Vector Stores' },
  { count: '8', label: 'Embedding Models' },
  { count: '4', label: 'Rerankers' },
  { count: '27+', label: 'Data Sources' },
  { count: '3', label: 'Payment Processors' },
];

export function TechStackSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section className="border-t border-border overflow-hidden" style={{ padding: '4rem 0' }}>
      <div ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="landing-container flex flex-col items-center gap-2 text-center mb-14"
        >
          <span className="landing-section-label">Integrations</span>
          <h2 className="landing-section-heading">Works with your entire stack</h2>
          <p className="landing-section-sub mx-auto">
            No vendor lock-in. Every integration is swappable via config — zero code changes.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="flex flex-col gap-4"
        >
          <MarqueeRow items={ROW_1} reverse={false} duration={55} />
          <MarqueeRow items={ROW_2} reverse={true} duration={48} />
          <MarqueeRow items={ROW_3} reverse={false} duration={52} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="landing-container mt-12"
        >
          <div className="flex flex-wrap items-center mt-8 -mb-5 justify-center gap-x-8 gap-y-4 rounded-xl border border-border bg-card/50 px-8 py-5">
            {COUNTS.map((s, i) => (
              <div key={s.label} className="flex items-center gap-2">
                {i > 0 && (
                  <div className="hidden sm:block h-3 w-px bg-border mr-6" />
                )}
                <span className="text-base font-bold font-mono text-foreground">{s.count}</span>
                <span className="text-xs text-muted-foreground">{s.label}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

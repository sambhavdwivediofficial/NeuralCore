// frontend/components/landing/TechStackSection.jsx

'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const STACK = {
  'LLM Providers': ['OpenAI', 'Anthropic', 'Google Gemini', 'DeepSeek', 'Mistral', 'Llama', 'Ollama'],
  'Vector Stores': ['Qdrant', 'Milvus', 'Weaviate', 'PGVector', 'Elasticsearch', 'FAISS'],
  'Embeddings': ['OpenAI', 'BGE', 'E5', 'Jina', 'Nomic', 'Sentence Transformers'],
  'Rerankers': ['BGE Reranker', 'Cross-Encoder', 'Jina Reranker', 'Hybrid'],
  'Infrastructure': ['FastAPI', 'PostgreSQL', 'Redis', 'Celery', 'Docker', 'Kubernetes'],
  'Payments': ['Stripe', 'Razorpay', 'PayPal'],
  'Observability': ['Prometheus', 'Grafana', 'Loki', 'OpenTelemetry'],
  'SDKs': ['Python', 'TypeScript', 'JavaScript', 'Go', 'Rust', 'Java'],
};

export function TechStackSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section className="landing-section border-t border-border bg-muted/10">
      <div className="landing-container" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-2 text-center mb-12"
        >
          <span className="landing-section-label">Integrations</span>
          <h2 className="landing-section-heading">Provider agnostic by design</h2>
          <p className="landing-section-sub mx-auto">
            No vendor lock-in. Swap any provider — LLM, vector store, embeddings, payments — via
            config. Your code never changes.
          </p>
        </motion.div>

        <div className="flex flex-col gap-6">
          {Object.entries(STACK).map(([category, items], ci) => (
            <motion.div
              key={category}
              initial={{ opacity: 0, y: 12 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: ci * 0.08 }}
              className="flex flex-col sm:flex-row items-start sm:items-center gap-3"
            >
              <span className="w-36 flex-shrink-0 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {category}
              </span>
              <div className="flex flex-wrap gap-2">
                {items.map((item) => (
                  <span key={item} className="landing-tech-pill">{item}</span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

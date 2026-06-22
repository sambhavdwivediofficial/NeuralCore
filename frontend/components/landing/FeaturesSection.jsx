// frontend/components/landing/FeaturesSection.jsx

'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
  Brain, Network, GitBranch, Shield, Zap, Database,
  Search, Bot, BookOpen, BarChart3, Puzzle, Cpu,
} from 'lucide-react';

const FEATURES = [
  {
    icon: Search,
    title: 'Production RAG',
    desc: 'Hybrid vector + BM25 retrieval with RRF fusion, HyDE query rewriting, BGE/Jina reranking, and context compression — all configurable per knowledge base.',
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
  },
  {
    icon: Bot,
    title: 'Agentic AI Runtime',
    desc: 'Stateful multi-agent system with 7 agent types, checkpointing, lifecycle management, A2A protocol, and a full tool framework — agents that survive restarts.',
    color: 'text-violet-500',
    bg: 'bg-violet-500/10',
  },
  {
    icon: Brain,
    title: '5-Layer Memory',
    desc: 'Short-term (Redis), long-term (Postgres), semantic (vector), episodic (time-indexed), and session memory. Agents remember across conversations.',
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
  },
  {
    icon: GitBranch,
    title: 'GraphRAG',
    desc: 'Entity extraction, relationship scoring, cross-document entity resolution, and graph traversal search. Multi-hop reasoning beyond similarity matching.',
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10',
  },
  {
    icon: Database,
    title: '6 Vector Backends',
    desc: 'Qdrant, Milvus, Weaviate, PGVector, Elasticsearch, and FAISS — unified abstraction layer. Switch backends via config, zero code changes.',
    color: 'text-cyan-500',
    bg: 'bg-cyan-500/10',
  },
  {
    icon: Cpu,
    title: 'Rust Performance Engine',
    desc: 'HNSW indexing, SIMD cosine similarity, cross-encoder reranking, tokenization, and LRU/LFU caching — all compiled Rust exposed via PyO3 FFI.',
    color: 'text-orange-500',
    bg: 'bg-orange-500/10',
  },
  {
    icon: Network,
    title: 'Multi-Agent Orchestration',
    desc: 'Planner, Executor, Research, Coding, Retrieval, Memory, and Tool agents — with direct, broadcast, queue, and request-reply A2A communication patterns.',
    color: 'text-pink-500',
    bg: 'bg-pink-500/10',
  },
  {
    icon: Shield,
    title: 'Enterprise Multi-Tenancy',
    desc: 'Full tenant isolation at DB, vector store, cache, and agent layers. RBAC with 5 roles, quota enforcement, audit logging, and compliance controls.',
    color: 'text-red-500',
    bg: 'bg-red-500/10',
  },
  {
    icon: BookOpen,
    title: '27+ Data Sources',
    desc: 'PDF, DOCX, GitHub, Notion, Confluence, Slack, Jira, PostgreSQL, YouTube, audio, video, and more — unified ingestion pipeline with PII detection.',
    color: 'text-yellow-500',
    bg: 'bg-yellow-500/10',
  },
  {
    icon: Zap,
    title: 'Fine-Tuning Pipeline',
    desc: 'LoRA and QLoRA adapter training, Alpaca/ShareGPT/OpenAI dataset formats, job queue with progress streaming, and model registry — on your hardware.',
    color: 'text-lime-500',
    bg: 'bg-lime-500/10',
  },
  {
    icon: BarChart3,
    title: 'Evaluation Framework',
    desc: 'Faithfulness, relevance, context precision/recall, NDCG, MRR, agent task success — automated benchmarks with trend tracking and quality reports.',
    color: 'text-sky-500',
    bg: 'bg-sky-500/10',
  },
  {
    icon: Puzzle,
    title: 'MCP + Plugin Ecosystem',
    desc: 'Model Context Protocol server and client, GitHub/Slack/Notion/Jira built-in plugins, and a plugin registry for custom integrations — loadable at runtime.',
    color: 'text-indigo-500',
    bg: 'bg-indigo-500/10',
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const cardVariant = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] } },
};

export function FeaturesSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="features" className="landing-section">
      <div className="landing-container" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-2 text-center mb-12"
        >
          <span className="landing-section-label">Platform capabilities</span>
          <h2 className="landing-section-heading">Everything your AI product needs</h2>
          <p className="landing-section-sub mx-auto">
            Not a wrapper. Not a demo. A complete, modular, production-grade AI infrastructure
            platform — provider-agnostic from day one.
          </p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          animate={inView ? 'show' : 'hidden'}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {FEATURES.map((f) => (
            <motion.div key={f.title} variants={cardVariant} className="landing-feature-card">
              <div className="flex items-start gap-3">
                <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${f.bg} ${f.color}`}>
                  <f.icon className="h-4.5 w-4.5" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-sm font-semibold text-foreground">{f.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

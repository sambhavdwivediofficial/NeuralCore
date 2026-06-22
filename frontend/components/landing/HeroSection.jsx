// frontend/components/landing/HeroSection.jsx

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Github, Zap } from 'lucide-react';
import { ROUTES } from '@/lib/routes';

const TERMINAL_LINES = [
  { delay: 0.2, type: 'prompt', text: 'neuralcore pipeline run --type agentic_rag' },
  { delay: 0.8, type: 'comment', text: '# Initializing hybrid retrieval pipeline...' },
  { delay: 1.2, type: 'key', text: '✓ ', suffix: 'Query rewritten via HyDE', suffixType: 'string' },
  { delay: 1.6, type: 'key', text: '✓ ', suffix: 'Vector search  → 847 chunks indexed', suffixType: 'normal' },
  { delay: 2.0, type: 'key', text: '✓ ', suffix: 'BM25 fusion    → RRF k=60', suffixType: 'normal' },
  { delay: 2.4, type: 'key', text: '✓ ', suffix: 'BGE reranker   → top 10 results', suffixType: 'normal' },
  { delay: 2.8, type: 'key', text: '✓ ', suffix: 'Roxan 48B      → answer generated', suffixType: 'string' },
  { delay: 3.2, type: 'success', text: '  Latency: 312ms  ·  Tokens: 1,847  ·  Sources: 6' },
];

function TerminalLine({ line, index }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), line.delay * 1000);
    return () => clearTimeout(t);
  }, [line.delay]);

  if (!visible) return null;

  const colorMap = {
    prompt: 'landing-terminal-prompt',
    comment: 'landing-terminal-comment',
    key: 'landing-terminal-key',
    string: 'landing-terminal-string',
    normal: '',
    success: 'landing-terminal-success',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
      className={`${colorMap[line.type] || ''}`}
    >
      {line.type === 'prompt' && <span className="landing-terminal-comment mr-2">$</span>}
      <span>{line.text}</span>
      {line.suffix && (
        <span className={colorMap[line.suffixType] || ''}>{line.suffix}</span>
      )}
    </motion.div>
  );
}

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94], delay: i * 0.1 },
  }),
};

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden">
      <div className="landing-grid-bg absolute inset-0 pointer-events-none" />
      <div className="landing-radial-fade absolute inset-0 pointer-events-none" />

      <div className="landing-container landing-section relative z-10">
        <div className="flex flex-col items-center text-center gap-6 max-w-4xl mx-auto">
          <motion.div variants={fadeUp} initial="hidden" animate="show" custom={0}>
            <span className="landing-badge">
              <Zap className="h-3 w-3" />
              Now in active development — Beta approaching
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={1}
            className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.08]"
          >
            The AI infrastructure
            <br />
            <span className="landing-gradient-text">platform for what</span>
            <br />
            comes next.
          </motion.h1>

          <motion.p
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={2}
            className="text-lg sm:text-xl text-muted-foreground max-w-2xl leading-relaxed"
          >
            NeuralCore unifies RAG, Agentic AI, Multi-Agent Orchestration, Knowledge Graphs,
            Fine-Tuning, and Enterprise Multi-Tenancy into one production-grade platform — so you
            ship AI products, not glue code.
          </motion.p>

          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={3}
            className="flex flex-col sm:flex-row items-center gap-3"
          >
            <Link
              href={ROUTES.SIGNUP}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-all hover:opacity-90 hover:scale-[1.02] landing-glow"
            >
              Start building free <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="https://github.com/sambhavdwivediofficial/NeuralCore"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
            >
              <Github className="h-4 w-4" /> View on GitHub
            </a>
          </motion.div>

          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={4}
            className="w-full max-w-2xl mt-4"
          >
            <div className="landing-terminal landing-glow">
              <div className="landing-terminal-bar">
                <div className="landing-terminal-dot bg-[#ff5f57]" />
                <div className="landing-terminal-dot bg-[#febc2e]" />
                <div className="landing-terminal-dot bg-[#28c840]" />
                <span className="ml-2 text-[0.6875rem] text-muted-foreground">neuralcore — zsh</span>
              </div>
              <div className="landing-terminal-body min-h-[9rem] flex flex-col gap-0.5">
                {TERMINAL_LINES.map((line, i) => (
                  <TerminalLine key={i} line={line} index={i} />
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

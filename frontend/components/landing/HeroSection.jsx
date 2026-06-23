// frontend/components/landing/HeroSection.jsx

'use client';

import { useEffect, useRef } from 'react';
import Link from 'next/link';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight, Github } from 'lucide-react';
import { ROUTES } from '@/lib/routes';

const WORDS = ['RAG Pipelines', 'Agent Networks', 'Knowledge Graphs', 'Fine-Tuning', 'Multi-Tenancy'];

function RotatingWord() {
  const [index, setIndex] = React.useState(0);

  useEffect(() => {
    const t = setInterval(() => setIndex((i) => (i + 1) % WORDS.length), 2200);
    return () => clearInterval(t);
  }, []);

  return (
    <span className="relative inline-block overflow-hidden" style={{ minWidth: '14ch' }}>
      <motion.span
        key={index}
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -40, opacity: 0 }}
        transition={{ duration: 0.42, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="inline-block text-primary"
      >
        {WORDS[index]}
      </motion.span>
    </span>
  );
}

const LOGOS = [
  { name: 'FastAPI', abbr: 'API' },
  { name: 'Qdrant', abbr: 'QD' },
  { name: 'OpenAI', abbr: 'OAI' },
  { name: 'Rust', abbr: 'RS' },
  { name: 'Postgres', abbr: 'PG' },
  { name: 'Redis', abbr: 'RD' },
  { name: 'Celery', abbr: 'CL' },
  { name: 'Ollama', abbr: 'OL' },
];

const STATS = [
  { value: '48B', label: 'Local Model' },
  { value: '<10ms', label: 'Rerank P99' },
  { value: '8', label: 'LLM Providers' },
  { value: '27+', label: 'Data Sources' },
];

import React from 'react';

export function HeroSection() {
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end start'] });
  const y = useTransform(scrollYProgress, [0, 1], ['0%', '20%']);
  const opacity = useTransform(scrollYProgress, [0.5, 1], [1, 0]);

  return (
    <section ref={containerRef} className="relative min-h-screen flex flex-col justify-center pt-16 overflow-hidden bg-background">
      <div className="absolute inset-0 pointer-events-none select-none">
        <div className="absolute inset-0 landing-grid-bg opacity-40" />
        <div
          className="absolute left-1/2 top-0 -translate-x-1/2 h-[600px] w-[900px] rounded-full opacity-[0.07]"
          style={{ background: 'radial-gradient(ellipse, hsl(var(--primary)) 0%, transparent 70%)', filter: 'blur(40px)' }}
        />
        <div
          className="absolute right-0 bottom-1/3 h-[400px] w-[400px] rounded-full opacity-[0.04]"
          style={{ background: 'radial-gradient(ellipse, hsl(280 65% 60%) 0%, transparent 70%)', filter: 'blur(60px)' }}
        />
      </div>

      <motion.div style={{ y, opacity }} className="landing-container px-4 sm:px-6 relative z-10">
        <div className="flex flex-col lg:flex-row items-center gap-16 lg:gap-24 min-h-[calc(100vh-4rem)] py-16 lg:py-0 lg:min-h-0">

          <div className="flex-1 flex flex-col gap-8 text-center lg:text-left">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="inline-flex items-center gap-2 self-center lg:self-start rounded-full border border-border bg-card px-3.5 py-1.5 text-xs font-medium text-muted-foreground"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              Active development · Beta approaching
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="flex flex-col gap-3"
            >
              <h1 className="text-[2.75rem] sm:text-5xl lg:text-[3.5rem] xl:text-6xl font-bold tracking-[-0.03em] leading-[1.06] text-foreground">
                Production AI infra
                <br className="hidden sm:block" />
                {' '}for teams that
                <br />
                <RotatingWord />
              </h1>
              <p className="text-base sm:text-lg text-muted-foreground leading-relaxed max-w-lg mx-auto lg:mx-0">
                One platform — RAG, agents, knowledge graphs, fine-tuning, multi-tenancy.
                Deploy in minutes. Scale to enterprise.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.38 }}
              className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3"
            >
              <Link
                href={ROUTES.SIGNUP}
                className="group inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:opacity-92 hover:-translate-y-0.5 active:translate-y-0"
              >
                Start building free
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a
                href="https://github.com/sambhavdwivediofficial/NeuralCore"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-5 py-2.5 text-sm font-medium text-foreground transition-all hover:bg-muted hover:-translate-y-0.5 active:translate-y-0"
              >
                <Github className="h-3.5 w-3.5" />
                View source
              </a>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.55 }}
              className="flex items-center justify-center lg:justify-start gap-6"
            >
              {STATS.map((s) => (
                <div key={s.label} className="flex flex-col items-center lg:items-start gap-0.5">
                  <span className="text-lg font-bold tracking-tight text-foreground font-mono">{s.value}</span>
                  <span className="text-[0.6875rem] text-muted-foreground uppercase tracking-wide">{s.label}</span>
                </div>
              ))}
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="flex-1 w-full max-w-md lg:max-w-none"
          >
            <div className="relative">
              <div
                className="absolute -inset-4 rounded-2xl opacity-30 blur-2xl pointer-events-none"
                style={{ background: 'radial-gradient(ellipse, hsl(var(--primary) / 0.4) 0%, transparent 70%)' }}
              />

              <div className="relative rounded-xl border border-border bg-card overflow-hidden shadow-2xl shadow-black/10">
                <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-muted/30">
                  <div className="flex gap-1.5">
                    <div className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
                    <div className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
                    <div className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
                  </div>
                  <span className="text-[0.6875rem] text-muted-foreground font-mono">agentic_rag_pipeline.py</span>
                  <div className="w-12" />
                </div>

                <div className="p-5 font-mono text-[0.75rem] leading-relaxed overflow-hidden">
                  <div className="flex flex-col gap-0.5">
                    {[
                      { t: 'comment', c: '# Initialize the NeuralCore client' },
                      { t: 'kw', c: 'from', rest: ' neuralcore import NeuralCore' },
                      { t: 'blank' },
                      { t: 'kw', c: 'client', rest: ' = NeuralCore(api_key=', end: '"nc_...")', endT: 'str' },
                      { t: 'blank' },
                      { t: 'comment', c: '# Run agentic RAG pipeline' },
                      { t: 'kw', c: 'result', rest: ' = client.pipelines.run(' },
                      { t: 'indent', c: '    query=', str: '"What is our Q3 revenue?",' },
                      { t: 'indent', c: '    knowledge_base_id=', str: '"kb_finance_2026",' },
                      { t: 'indent', c: '    pipeline_type=', str: '"agentic_rag",' },
                      { t: 'indent', c: '    agent_ids=[', str: '"agent_research"', end: '],' },
                      { t: 'close', c: ')' },
                      { t: 'blank' },
                      { t: 'comment', c: '# Streamed answer + cited sources' },
                      { t: 'kw', c: 'print', rest: '(result.answer)' },
                      { t: 'kw', c: 'print', rest: '(result.sources)' },
                    ].map((line, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.25, delay: 0.6 + i * 0.04 }}
                      >
                        {line.t === 'blank' && <div className="h-3" />}
                        {line.t === 'comment' && (
                          <span className="text-muted-foreground/60">{line.c}</span>
                        )}
                        {(line.t === 'kw' || line.t === 'indent') && (
                          <span>
                            <span className="text-warning">{line.c}</span>
                            {line.rest && <span className="text-foreground/80">{line.rest}</span>}
                            {line.str && <span className="text-success">{line.str}</span>}
                            {line.end && <span className={line.endT === 'str' ? 'text-success' : 'text-foreground/80'}>{line.end}</span>}
                          </span>
                        )}
                        {line.t === 'close' && <span className="text-foreground/80">{line.c}</span>}
                      </motion.div>
                    ))}
                  </div>
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 1.5 }}
                  className="border-t border-border bg-success/5 px-5 py-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
                    <span className="text-[0.6875rem] text-success font-medium">Pipeline completed</span>
                  </div>
                  <span className="text-[0.6875rem] text-muted-foreground font-mono">312ms · 6 sources</span>
                </motion.div>
              </div>

              <div className="mt-4 grid grid-cols-4 gap-2">
                {LOGOS.map((l, i) => (
                  <motion.div
                    key={l.name}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.9 + i * 0.05 }}
                    className="flex items-center justify-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5"
                  >
                    <span className="text-[0.625rem] font-bold text-primary font-mono">{l.abbr}</span>
                    <span className="text-[0.625rem] text-muted-foreground hidden sm:inline">{l.name}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.8, duration: 0.8 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5"
      >
        <span className="text-[0.625rem] uppercase tracking-widest text-muted-foreground/50">Scroll</span>
        <motion.div
          animate={{ y: [0, 5, 0] }}
          transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
          className="h-4 w-px bg-gradient-to-b from-muted-foreground/40 to-transparent"
        />
      </motion.div>
    </section>
  );
}

// frontend/components/landing/MetricsSection.jsx

'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, useInView } from 'framer-motion';

const METRICS = [
  { value: 8, suffix: '', label: 'LLM Providers', prefix: '' },
  { value: 6, suffix: '', label: 'Vector Backends', prefix: '' },
  { value: 27, suffix: '+', label: 'Data Sources', prefix: '' },
  { value: 5, suffix: '', label: 'Memory Layers', prefix: '' },
  { value: 10, suffix: 'ms', label: 'Rerank Latency', prefix: '<' },
  { value: 48, suffix: 'B', label: 'Local Model Params', prefix: '' },
  { value: 58, suffix: '', label: 'Engine Tests Passing', prefix: '' },
  { value: 100, suffix: '%', label: 'Modular Architecture', prefix: '' },
];

function Counter({ target, prefix = '', suffix = '', duration = 1800 }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  useEffect(() => {
    if (!inView) return;
    const start = performance.now();
    const tick = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(ease * target));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [inView, target, duration]);

  return (
    <span ref={ref} className="landing-metric-value">
      {prefix}{count}{suffix}
    </span>
  );
}

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] } },
};

export function MetricsSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="metrics" className="landing-section border-y border-border bg-muted/20">
      <div className="landing-container" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-2 text-center mb-12"
        >
          <span className="landing-section-label">By the numbers</span>
          <h2 className="landing-section-heading">Built for production scale</h2>
          <p className="landing-section-sub mx-auto">
            Every number is real — pulled directly from the architecture, benchmarks, and live configuration.
          </p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          animate={inView ? 'show' : 'hidden'}
          className="grid grid-cols-2 sm:grid-cols-4 gap-4"
        >
          {METRICS.map((m) => (
            <motion.div key={m.label} variants={item} className="landing-metric-card">
              <Counter target={m.value} prefix={m.prefix} suffix={m.suffix} />
              <span className="landing-metric-label">{m.label}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// frontend/components/landing/CTASection.jsx

'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ArrowRight, Github } from 'lucide-react';
import Link from 'next/link';
import { ROUTES } from '@/lib/routes';

export function CTASection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section className="landing-section border-t border-border" ref={ref}>
      <div className="landing-container">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.55 }}
          className="relative overflow-hidden rounded-2xl border border-border bg-card p-10 sm:p-16 text-center"
        >
          <div className="landing-radial-fade absolute inset-0 pointer-events-none" />
          <div className="relative z-10 flex flex-col items-center gap-6 max-w-2xl mx-auto">
            <h2 className="landing-section-heading">
              Ready to build the future of AI?
            </h2>
            <p className="landing-section-sub">
              Start with a 14-day free trial. No credit card. Full platform access from day one —
              deploy locally or to the cloud in minutes.
            </p>
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <Link
                href={ROUTES.SIGNUP}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition-all hover:opacity-90 hover:scale-[1.02] landing-glow"
              >
                Start building free <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="https://github.com/sambhavdwivediofficial/NeuralCore"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-border px-6 py-2.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
              >
                <Github className="h-4 w-4" /> Star on GitHub
              </a>
            </div>
            <p className="text-xs text-muted-foreground">
              Built with precision by{' '}
              <a
                href="https://www.sambhavdwivedi.in"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline font-medium"
              >
                Sambhav Dwivedi
              </a>
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// frontend/components/landing/PricingSection.jsx

'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Check, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { ROUTES } from '@/lib/routes';

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: 'Free',
    period: '14-day trial',
    description: 'Explore the full platform. No credit card required.',
    cta: 'Start free trial',
    href: ROUTES.SIGNUP,
    featured: false,
    features: [
      '1 organization',
      '3 projects',
      '5 agents',
      '2 knowledge bases',
      '500MB document storage',
      '50K tokens / day',
      'Qdrant vector store',
      'Community support',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$49',
    period: 'per month',
    description: 'For teams building serious AI products.',
    cta: 'Get started',
    href: ROUTES.SIGNUP,
    featured: true,
    badge: 'Most popular',
    features: [
      'Unlimited projects',
      '50 agents',
      '20 knowledge bases',
      '20GB document storage',
      '2M tokens / day',
      'All 6 vector backends',
      'GraphRAG + Knowledge Graph',
      'Fine-tuning pipeline',
      'SSE agent streaming',
      'Priority support',
    ],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    period: 'contact us',
    description: 'Dedicated infrastructure with SLA guarantees.',
    cta: 'Contact sales',
    href: 'mailto:sambhavdwivedi@outlook.com',
    featured: false,
    features: [
      'Everything in Pro',
      'Unlimited agents & storage',
      'Dedicated Kubernetes cluster',
      'Custom model fine-tuning',
      'Distributed training (DDP/FSDP)',
      'SOC 2 / HIPAA ready',
      'Custom SLA + uptime',
      'Dedicated solutions engineer',
    ],
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const card = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] } },
};

export function PricingSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="pricing" className="landing-section border-t border-border">
      <div className="landing-container" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-2 text-center mb-12"
        >
          <span className="landing-section-label">Pricing</span>
          <h2 className="landing-section-heading">Start free, scale when ready</h2>
          <p className="landing-section-sub mx-auto">
            No vendor lock-in, no per-seat pricing games. Pay for what your platform actually uses.
          </p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          animate={inView ? 'show' : 'hidden'}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start"
        >
          {PLANS.map((plan) => (
            <motion.div
              key={plan.id}
              variants={card}
              className="landing-pricing-card"
              data-featured={plan.featured ? 'true' : 'false'}
            >
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-foreground">{plan.name}</span>
                  {plan.badge && (
                    <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary border border-primary/20">
                      {plan.badge}
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-3xl font-bold tracking-tight text-foreground">{plan.price}</span>
                  <span className="text-xs text-muted-foreground">{plan.period}</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">{plan.description}</p>
              </div>

              <Link
                href={plan.href}
                className={`flex items-center justify-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium transition-all ${
                  plan.featured
                    ? 'bg-primary text-primary-foreground hover:opacity-90'
                    : 'border border-border bg-card text-foreground hover:bg-muted'
                }`}
              >
                {plan.cta} <ArrowRight className="h-3.5 w-3.5" />
              </Link>

              <ul className="flex flex-col gap-2.5">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-xs text-muted-foreground">
                    <Check className="h-3.5 w-3.5 flex-shrink-0 mt-0.5 text-success" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

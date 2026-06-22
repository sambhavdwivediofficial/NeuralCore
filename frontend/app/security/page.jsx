// frontend/app/security/page.jsx

import Link from 'next/link';
import { Sparkles, ArrowLeft, Shield, Lock, Eye, Key, Server, AlertTriangle } from 'lucide-react';
import '@/styles/landing.css';
import { LandingFooter } from '@/components/landing/LandingFooter';

export const metadata = {
  title: 'Security — NeuralCore',
  description: 'NeuralCore security architecture, practices, and responsible disclosure.',
};

const PILLARS = [
  {
    icon: Lock,
    title: 'Encryption everywhere',
    items: [
      'TLS 1.3 for all data in transit',
      'AES-256 encryption for data at rest',
      'JWT RS256 asymmetric signing',
      'bcrypt-hashed credentials (cost factor 12)',
      'API keys stored as bcrypt hashes — plaintext shown once',
    ],
  },
  {
    icon: Shield,
    title: 'Multi-tenant isolation',
    items: [
      'Tenant context enforced at database query level (mandatory tenant_id filter)',
      'Vector store collections namespaced per tenant',
      'Redis keys prefixed with tenant ID — no cache collision',
      'Agent runtimes isolated per tenant',
      'Inter-tenant API communication blocked at routing layer',
    ],
  },
  {
    icon: Key,
    title: 'Authentication & authorization',
    items: [
      '5-role RBAC: super_admin > owner > admin > developer > viewer',
      'Short-lived access tokens (15 min) + rolling refresh tokens (30 days)',
      'TOTP-based multi-factor authentication (RFC 6238)',
      'OAuth 2.0 via Google, GitHub, Microsoft',
      'Session revocation and device management',
    ],
  },
  {
    icon: Eye,
    title: 'Audit & compliance',
    items: [
      'Comprehensive audit logging for all significant operations',
      'Sensitive field sanitization in logs (tokens, API keys, emails, card numbers)',
      'PII detection and configurable redaction in ingestion pipeline',
      'OpenTelemetry distributed tracing — full request lineage',
      'Prometheus metrics + Grafana alerting for anomaly detection',
    ],
  },
  {
    icon: Server,
    title: 'Infrastructure security',
    items: [
      'Fail-safe defaults — authentication required everywhere by default',
      'Rate limiting and quota enforcement at middleware level',
      'Dependency vulnerability scanning (cargo audit, npm audit) in CI',
      'Docker images built from minimal base images, non-root users',
      'Kubernetes NetworkPolicy — explicit pod-to-pod allowlists',
      'Secret management via environment variables and Vault/AWS Secrets Manager',
    ],
  },
];

export default function SecurityPage() {
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

      <div className="landing-container px-4 sm:px-6 py-12 sm:py-16 max-w-4xl">
        <div className="flex flex-col gap-3 mb-12">
          <span className="landing-section-label">Security</span>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Security is built in, not bolted on
          </h1>
          <p className="text-base text-muted-foreground leading-relaxed max-w-2xl">
            Every security control in NeuralCore is a foundational constraint — enforced at the
            architecture level, not as an afterthought layer. Fail-safe defaults mean you have to
            explicitly relax restrictions, never explicitly add them.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-16">
          {PILLARS.map((pillar) => (
            <div key={pillar.title} className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <pillar.icon className="h-4 w-4" />
                </div>
                <h2 className="text-sm font-semibold text-foreground">{pillar.title}</h2>
              </div>
              <ul className="flex flex-col gap-2">
                {pillar.items.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="mt-1.5 h-1 w-1 flex-shrink-0 rounded-full bg-primary" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-warning/30 bg-warning/5 p-6 flex flex-col sm:flex-row gap-4">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-warning/10 text-warning">
            <AlertTriangle className="h-4.5 w-4.5" />
          </div>
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-foreground">Responsible Disclosure</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              If you discover a security vulnerability in NeuralCore, please report it responsibly.
              Do not disclose vulnerabilities publicly until we have had a reasonable opportunity to
              address them. We take all reports seriously and will acknowledge receipt within 48 hours.
            </p> 
            <a
              href="mailto:sambhavdwivedi@outlook.com?subject=NeuralCore Security Vulnerability"
              className="text-xs font-medium text-primary hover:underline w-fit"
            >
              Report a vulnerability → sambhavdwivedi@outlook.com
            </a>
          </div>
        </div>
      </div>

      <LandingFooter />
    </div>
  );
}

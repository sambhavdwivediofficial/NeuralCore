// frontend/components/landing/LandingFooter.jsx

import Link from 'next/link';
import { Sparkles, Github, Linkedin, Globe } from 'lucide-react';

const FOOTER_LINKS = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'Pricing', href: '#pricing' },
    { label: 'Changelog', href: '/changelog' },
    { label: 'Security', href: '/security' },
    { label: 'Dashboard', href: '/dashboard' },
  ],
  Platform: [
    { label: 'RAG Pipelines', href: '#features' },
    { label: 'Agent System', href: '#features' },
    { label: 'Knowledge Bases', href: '#features' },
    { label: 'Vector Stores', href: '#features' },
    { label: 'Fine-Tuning', href: '#features' },
  ],
  Developers: [
    { label: 'API Reference', href: 'http://localhost:8000/api/v1/docs', external: true },
    { label: 'GitHub', href: 'https://github.com/sambhavdwivediofficial/NeuralCore', external: true },
    { label: 'Architecture', href: '/architecture' },
    { label: 'Sign up', href: '/signup' },
    { label: 'Sign in', href: '/login' },
  ],
  Legal: [
    { label: 'Privacy Policy', href: '/privacy' },
    { label: 'Terms of Service', href: '/terms' },
    { label: 'Security', href: '/security' },
  ],
};

const SOCIALS = [
  {
    label: 'GitHub',
    href: 'https://github.com/sambhavdwivediofficial/NeuralCore',
    icon: Github,
  },
  {
    label: 'LinkedIn',
    href: 'https://www.linkedin.com/in/sambhavdwivedi',
    icon: Linkedin,
  },
  {
    label: 'Website',
    href: 'https://www.sambhavdwivedi.in',
    icon: Globe,
  },
];

export function LandingFooter() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="landing-container px-4 sm:px-6 py-12 sm:py-16">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-5">
          <div className="lg:col-span-1 flex flex-col gap-4">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Sparkles className="h-4 w-4" />
              </div>
              <span className="text-sm font-semibold tracking-tight text-foreground">NeuralCore</span>
            </Link>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xs">
              Enterprise AI infrastructure platform for RAG, Agentic AI, multi-agent orchestration,
              and knowledge management.
            </p>
            <div className="flex items-center gap-2">
              {SOCIALS.map((s) => (
                <a
                  key={s.label}
                  href={s.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={s.label}
                  className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <s.icon className="h-3.5 w-3.5" />
                </a>
              ))}
            </div>
          </div>

          <div className="lg:col-span-4 grid grid-cols-2 sm:grid-cols-4 gap-8">
            {Object.entries(FOOTER_LINKS).map(([category, links]) => (
              <div key={category} className="flex flex-col gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  {category}
                </span>
                <ul className="flex flex-col gap-2">
                  {links.map((link) => (
                    <li key={link.label}>
                      {link.external ? (
                        <a
                          href={link.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {link.label}
                        </a>
                      ) : (
                        <Link
                          href={link.href}
                          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {link.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} NeuralCore. All rights reserved.
          </p>
          <p className="text-xs text-muted-foreground">
            Built & Maintained by{' '}
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
      </div>
    </footer>
  );
}

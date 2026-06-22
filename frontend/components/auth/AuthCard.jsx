// frontend/components/auth/AuthCard.jsx

import { Sparkles } from 'lucide-react';
import Link from 'next/link';

export function AuthCard({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <Link href="/" className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-opacity hover:opacity-90">
            <Sparkles className="h-5 w-5" />
          </Link>
          <div className="flex flex-col items-center gap-1 text-center">
            <h1 className="text-lg font-semibold tracking-tight text-foreground">{title}</h1>
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
        </div>

        <div className="card-surface flex flex-col gap-4 p-6">
          {children}
        </div>

        {footer && (
          <div className="mt-6 text-center text-xs text-muted-foreground">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

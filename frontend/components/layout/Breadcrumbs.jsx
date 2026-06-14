// components/layout/Breadcrumbs.jsx

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight, Home } from 'lucide-react';
import { Fragment } from 'react';

const LABEL_OVERRIDES = {
  'knowledge-bases': 'Knowledge Bases',
  'vector-stores': 'Vector Stores',
  'retrieval-debugger': 'Retrieval Debugger',
  'api-keys': 'API Keys',
};

function formatSegment(segment) {
  if (LABEL_OVERRIDES[segment]) return LABEL_OVERRIDES[segment];
  if (/^[a-f0-9-]{8,}$/i.test(segment)) return 'Details';
  return segment
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0) {
    return null;
  }

  return (
    <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <Link href="/dashboard" className="flex items-center transition-colors hover:text-foreground">
        <Home className="h-3.5 w-3.5" />
      </Link>
      {segments.map((segment, index) => {
        const href = `/${segments.slice(0, index + 1).join('/')}`;
        const isLast = index === segments.length - 1;
        const label = formatSegment(segment);

        return (
          <Fragment key={href}>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
            {isLast ? (
              <span className="font-medium text-foreground">{label}</span>
            ) : (
              <Link href={href} className="transition-colors hover:text-foreground">
                {label}
              </Link>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}

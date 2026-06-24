// frontend/components/chat/SourceCitations.jsx

'use client';

import { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);
  const score = typeof source.score === 'number' ? (source.score * 100).toFixed(0) : null;

  return (
    <div className="chat-source-card" onClick={() => setExpanded((p) => !p)}>
      <div className="flex items-center gap-2.5">
        <div className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-primary/10 text-primary text-[0.625rem] font-bold">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <FileText className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
            <span className="truncate text-xs font-medium text-foreground">
              {source.metadata?.filename ?? source.metadata?.source ?? `Source ${index + 1}`}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {score && (
            <span className={cn(
              'text-[0.625rem] font-semibold px-1.5 py-0.5 rounded',
              Number(score) >= 80 ? 'text-success bg-success/10' :
              Number(score) >= 60 ? 'text-warning bg-warning/10' : 'text-muted-foreground bg-muted'
            )}>
              {score}%
            </span>
          )}
          {expanded ? <ChevronUp className="h-3 w-3 text-muted-foreground" /> : <ChevronDown className="h-3 w-3 text-muted-foreground" />}
        </div>
      </div>

      {expanded && source.text && (
        <div className="mt-2.5 pt-2.5 border-t border-border">
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-6">{source.text}</p>
          {source.metadata?.page && (
            <span className="mt-1.5 inline-block text-[0.625rem] text-muted-foreground/60">
              Page {source.metadata.page}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function SourceCitations({ sources = [] }) {
  const [show, setShow] = useState(true);
  if (!sources.length) return null;

  return (
    <div className="flex flex-col gap-2 mt-2">
      <button
        type="button"
        onClick={() => setShow((p) => !p)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-fit"
      >
        <FileText className="h-3 w-3" />
        {sources.length} source{sources.length > 1 ? 's' : ''}
        {show ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>
      {show && (
        <div className="flex flex-col gap-1.5">
          {sources.map((source, i) => (
            <SourceCard key={source.id ?? i} source={source} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

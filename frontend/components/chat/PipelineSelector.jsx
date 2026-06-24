// frontend/components/chat/PipelineSelector.jsx

'use client';

import { useState } from 'react';
import { ChevronDown, Zap, Search, GitBranch, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const PIPELINE_OPTIONS = [
  {
    id: 'rag',
    label: 'RAG',
    description: 'Hybrid vector + BM25 retrieval with reranking',
    icon: Search,
    color: 'text-blue-500',
  },
  {
    id: 'agentic_rag',
    label: 'Agentic RAG',
    description: 'Multi-step agent with tool use and memory',
    icon: Zap,
    color: 'text-violet-500',
  },
  {
    id: 'graphrag',
    label: 'GraphRAG',
    description: 'Knowledge graph multi-hop reasoning',
    icon: GitBranch,
    color: 'text-emerald-500',
  },
];

export function PipelineSelector({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const selected = PIPELINE_OPTIONS.find((p) => p.id === value) ?? PIPELINE_OPTIONS[0];
  const Icon = selected.icon;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors"
      >
        <Icon className={cn('h-3.5 w-3.5', selected.color)} />
        {selected.label}
        <ChevronDown className={cn('h-3 w-3 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute bottom-full left-0 mb-2 z-50 w-64 rounded-lg border border-border bg-popover shadow-lg py-1 overflow-hidden">
            {PIPELINE_OPTIONS.map((p) => {
              const PIcon = p.icon;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => { onChange(p.id); setOpen(false); }}
                  className="flex w-full items-start gap-3 px-3 py-2.5 text-left hover:bg-accent transition-colors"
                >
                  <div className={cn('mt-0.5 flex-shrink-0', p.color)}>
                    <PIcon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-foreground">{p.label}</span>
                      {selected.id === p.id && <Check className="h-3 w-3 text-primary" />}
                    </div>
                    <span className="text-[0.6875rem] text-muted-foreground leading-relaxed">{p.description}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// frontend/components/workflows/WorkflowCard.jsx

'use client';

import { useState } from 'react';
import { Play, Trash2, MoreHorizontal, Clock, GitBranch, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

const TEMPLATE_LABELS = {
  rag: 'RAG',
  agentic_rag: 'Agentic RAG',
  research: 'Research',
  code_assistant: 'Code Assistant',
  custom: 'Custom',
};

const TEMPLATE_COLORS = {
  rag: 'text-blue-500 bg-blue-500/10',
  agentic_rag: 'text-violet-500 bg-violet-500/10',
  research: 'text-emerald-500 bg-emerald-500/10',
  code_assistant: 'text-orange-500 bg-orange-500/10',
  custom: 'text-muted-foreground bg-muted',
};

export function WorkflowCard({ workflow, onRun, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const template = workflow.template ?? 'custom';

  return (
    <div className="workflow-card group">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={cn('flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md text-sm font-semibold', TEMPLATE_COLORS[template] ?? TEMPLATE_COLORS.custom)}>
            <GitBranch className="h-4 w-4" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-foreground truncate">{workflow.name}</span>
            <span className={cn('text-[0.6875rem] font-medium uppercase tracking-wide mt-0.5', TEMPLATE_COLORS[template]?.split(' ')[0] ?? 'text-muted-foreground')}>
              {TEMPLATE_LABELS[template] ?? template}
            </span>
          </div>
        </div>

        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => setMenuOpen((p) => !p)}
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground opacity-0 group-hover:opacity-100 hover:bg-accent hover:text-foreground transition-all"
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-lg border border-border bg-popover shadow-lg py-1 overflow-hidden">
                {onRun && (
                  <button
                    type="button"
                    onClick={() => { onRun(workflow); setMenuOpen(false); }}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-foreground hover:bg-accent"
                  >
                    <Play className="h-3.5 w-3.5 text-success" /> Run workflow
                  </button>
                )}
                {onDelete && (
                  <button
                    type="button"
                    onClick={() => { onDelete(workflow.id); setMenuOpen(false); }}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-destructive hover:bg-accent"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Delete
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {workflow.description && (
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
          {workflow.description}
        </p>
      )}

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Activity className="h-3 w-3" />
          <span>{workflow.run_count ?? 0} runs</span>
        </div>
        {workflow.updated_at && (
          <div className="flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            <span>{new Date(workflow.updated_at).toLocaleDateString()}</span>
          </div>
        )}
        {onRun && (
          <button
            type="button"
            onClick={() => onRun(workflow)}
            className="ml-auto flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/15 transition-colors"
          >
            <Play className="h-3 w-3" /> Run
          </button>
        )}
      </div>
    </div>
  );
}

// frontend/components/prompts/PromptCard.jsx

'use client';

import { FileText, Copy, ChevronRight } from 'lucide-react';
import { toast } from '@/components/common/Toast';
import { cn } from '@/lib/utils';

const CATEGORY_COLORS = {
  rag: 'text-blue-500 bg-blue-500/10',
  agent: 'text-violet-500 bg-violet-500/10',
  memory: 'text-emerald-500 bg-emerald-500/10',
  query: 'text-orange-500 bg-orange-500/10',
  default: 'text-muted-foreground bg-muted',
};

function getCategory(name = '') {
  if (name.includes('rag') || name.includes('qa')) return 'rag';
  if (name.includes('agent') || name.includes('tool')) return 'agent';
  if (name.includes('memory') || name.includes('summary')) return 'memory';
  if (name.includes('query') || name.includes('hyde') || name.includes('step')) return 'query';
  return 'default';
}

export function PromptCard({ template, onSelect }) {
  const cat = getCategory(template.name);
  const colorClass = CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.default;

  const copyTemplate = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(template.template ?? template.name).then(() => toast.success('Copied to clipboard'));
  };

  return (
    <div
      className={cn(
        'group flex flex-col gap-3 rounded-lg border border-border bg-card p-4 transition-all hover:border-primary/30 hover:shadow-sm',
        onSelect && 'cursor-pointer'
      )}
      onClick={() => onSelect?.(template)}
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onKeyDown={onSelect ? (e) => e.key === 'Enter' && onSelect(template) : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={cn('flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md', colorClass)}>
            <FileText className="h-4 w-4" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-foreground truncate font-mono">{template.name}</span>
            <span className={cn('text-[0.6875rem] font-medium uppercase tracking-wide mt-0.5', colorClass.split(' ')[0])}>
              {cat}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button type="button" onClick={copyTemplate}
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
            <Copy className="h-3.5 w-3.5" />
          </button>
          {onSelect && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
        </div>
      </div>

      {template.required_variables?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {template.required_variables.map((v) => (
            <span key={v} className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 font-mono text-[0.6875rem] text-muted-foreground">
              {'{{'}{v}{'}}'}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// frontend/components/datasets/DatasetCard.jsx

'use client';

import { useState } from 'react';
import { Database, Trash2, MoreHorizontal, FileText, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

const FORMAT_STYLES = {
  alpaca: 'text-emerald-500 bg-emerald-500/10',
  sharegpt: 'text-blue-500 bg-blue-500/10',
  openai: 'text-violet-500 bg-violet-500/10',
  custom: 'text-orange-500 bg-orange-500/10',
};

const STATUS_STYLES = {
  ready: 'text-success bg-success/10',
  processing: 'text-primary bg-primary/10',
  failed: 'text-destructive bg-destructive/10',
  empty: 'text-muted-foreground bg-muted',
};

export function DatasetCard({ dataset, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const format = dataset.format ?? 'custom';
  const status = dataset.status ?? 'empty';

  return (
    <div className="group flex flex-col gap-3 rounded-lg border border-border bg-card p-4 transition-all hover:border-primary/30 hover:shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={cn('flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md', FORMAT_STYLES[format] ?? FORMAT_STYLES.custom)}>
            <Database className="h-4 w-4" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-foreground truncate">{dataset.name}</span>
            <span className={cn('text-[0.6875rem] font-medium uppercase tracking-wide mt-0.5', FORMAT_STYLES[format]?.split(' ')[0] ?? 'text-muted-foreground')}>
              {format}
            </span>
          </div>
        </div>

        <div className="relative flex-shrink-0 flex items-center gap-2">
          <span className={cn('text-[0.6875rem] font-medium px-2 py-0.5 rounded-full capitalize', STATUS_STYLES[status] ?? STATUS_STYLES.empty)}>
            {status}
          </span>
          {onDelete && (
            <div className="relative">
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
                  <div className="absolute right-0 top-full mt-1 z-50 w-36 rounded-lg border border-border bg-popover shadow-lg py-1">
                    <button
                      type="button"
                      onClick={() => { onDelete(dataset.id); setMenuOpen(false); }}
                      className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-destructive hover:bg-accent"
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {dataset.description && (
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
          {dataset.description}
        </p>
      )}

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <FileText className="h-3 w-3" />
          <span>{(dataset.row_count ?? 0).toLocaleString()} rows</span>
        </div>
        {dataset.created_at && (
          <div className="flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            <span>{new Date(dataset.created_at).toLocaleDateString()}</span>
          </div>
        )}
      </div>
    </div>
  );
}

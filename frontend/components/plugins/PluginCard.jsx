// frontend/components/plugins/PluginCard.jsx

'use client';

import { useState } from 'react';
import { Github, MessageSquare, FileText, Trello, Puzzle, Check, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

const PLUGIN_ICONS = { github: Github, slack: MessageSquare, notion: FileText, jira: Trello };
const PLUGIN_COLORS = {
  github: 'bg-foreground/10 text-foreground',
  slack: 'bg-violet-500/10 text-violet-500',
  notion: 'bg-muted text-muted-foreground',
  jira: 'bg-blue-500/10 text-blue-500',
};

export function PluginCard({ plugin }) {
  const [enabled, setEnabled] = useState(plugin.enabled ?? false);
  const Icon = PLUGIN_ICONS[plugin.id] ?? Puzzle;
  const colorClass = PLUGIN_COLORS[plugin.id] ?? 'bg-muted text-muted-foreground';

  return (
    <div className={cn('flex flex-col gap-4 rounded-lg border bg-card p-5 transition-all', enabled ? 'border-primary/30' : 'border-border')}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={cn('flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg', colorClass)}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-foreground capitalize">{plugin.name ?? plugin.id}</span>
            <span className="text-xs text-muted-foreground">{plugin.category ?? 'Integration'}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setEnabled((p) => !p)}
          className={cn(
            'flex h-6 w-11 flex-shrink-0 items-center rounded-full border-2 transition-all duration-200',
            enabled ? 'border-primary bg-primary justify-end' : 'border-border bg-muted justify-start'
          )}
        >
          <span className={cn('h-4 w-4 rounded-full bg-background shadow-sm mx-0.5 transition-all', enabled && 'translate-x-0')} />
        </button>
      </div>

      <p className="text-xs text-muted-foreground leading-relaxed">
        {plugin.description ?? `Connect NeuralCore with ${plugin.name ?? plugin.id} to sync data and trigger workflows automatically.`}
      </p>

      <div className="flex items-center justify-between">
        <span className={cn('inline-flex items-center gap-1 text-xs font-medium', enabled ? 'text-success' : 'text-muted-foreground')}>
          {enabled ? <><Check className="h-3 w-3" /> Connected</> : 'Not connected'}
        </span>
        <a href={plugin.docs_url ?? '#'} target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-primary hover:underline">
          Docs <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

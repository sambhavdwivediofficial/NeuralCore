// frontend/app/plugins/page.jsx

'use client';

import { Puzzle } from 'lucide-react';
import { PluginCard } from '@/components/plugins/PluginCard';
import { Loader } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { usePlugins } from '@/hooks/usePlugins';

export default function PluginsPage() {
  const { plugins, isLoading, error } = usePlugins();

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-0.5">
        <h1 className="text-lg font-semibold text-foreground">Plugins</h1>
        <p className="text-xs text-muted-foreground">Connect NeuralCore with external services and tools</p>
      </div>

      {plugins.length === 0 ? (
        <EmptyState icon={Puzzle} title="No plugins available" description="Plugin integrations will appear here when available." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {plugins.map((plugin) => (
            <PluginCard key={plugin.id} plugin={plugin} />
          ))}
        </div>
      )}

      <div className="rounded-lg border border-border bg-card/50 p-4 flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Puzzle className="h-4 w-4" />
        </div>
        <div className="flex flex-col gap-0.5">
          <p className="text-sm font-medium text-foreground">Build a custom plugin</p>
          <p className="text-xs text-muted-foreground">Use the Plugin SDK to create integrations for any internal tool or API. Plugin registry is extensible at runtime.</p>
        </div>
      </div>
    </div>
  );
}

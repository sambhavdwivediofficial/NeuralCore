// frontend/app/prompts/page.jsx

'use client';

import { useState } from 'react';
import { FileText } from 'lucide-react';
import { PromptCard } from '@/components/prompts/PromptCard';
import { PromptPreview } from '@/components/prompts/PromptPreview';
import { PageLoader as Loader } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { SearchBar } from '@/components/common/SearchBar';
import { usePrompts } from '@/hooks/usePrompts';

export default function PromptsPage() {
  const { templates, isLoading, error } = usePrompts();
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);

  const filtered = templates.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-lg font-semibold text-foreground">Prompt Templates</h1>
          <p className="text-xs text-muted-foreground">{templates.length} built-in templates � render and preview before deploying</p>
        </div>
        <SearchBar value={search} onChange={setSearch} placeholder="Search templates�" className="w-56" />
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={FileText} title="No templates found" description="Try a different search term." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="flex flex-col gap-3">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Templates</p>
            <div className="flex flex-col gap-2">
              {filtered.map((t) => (
                <PromptCard
                  key={t.name}
                  template={t}
                  onSelect={(tmpl) => setSelected(selected?.name === tmpl.name ? null : tmpl)}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {selected ? `Preview � ${selected.name}` : 'Preview'}
            </p>
            {selected ? (
              <PromptPreview template={selected} />
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-border bg-card/50 p-10 text-center">
                <FileText className="h-8 w-8 text-muted-foreground/40" />
                <p className="text-xs text-muted-foreground">Select a template to preview and render it with variables</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


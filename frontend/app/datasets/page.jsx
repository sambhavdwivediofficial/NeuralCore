// frontend/app/datasets/page.jsx

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Database, Plus } from 'lucide-react';
import { DatasetCard } from '@/components/datasets/DatasetCard';
import { EmptyState } from '@/components/common/EmptyState';
import { Loader } from '@/components/common/Loader';
import { SearchBar } from '@/components/common/SearchBar';
import { useDatasets } from '@/hooks/useDatasets';
import { ROUTES } from '@/lib/routes';

export default function DatasetsPage() {
  const { datasets, isLoading, error, remove } = useDatasets();
  const [search, setSearch] = useState('');

  const filtered = datasets.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-lg font-semibold text-foreground">Datasets</h1>
          <p className="text-xs text-muted-foreground">{datasets.length} fine-tuning dataset{datasets.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          <SearchBar value={search} onChange={setSearch} placeholder="Search datasets…" className="w-56" />
          <Link href={ROUTES.DATASET_CREATE}
            className="flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
            <Plus className="h-3.5 w-3.5" /> New dataset
          </Link>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={Database}
          title={search ? 'No datasets match' : 'No datasets yet'}
          description={search ? 'Try a different search term.' : 'Create a dataset to start fine-tuning.'}
          action={!search ? { label: 'New dataset', href: ROUTES.DATASET_CREATE } : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((ds) => (
            <DatasetCard key={ds.id} dataset={ds} onDelete={remove} />
          ))}
        </div>
      )}
    </div>
  );
}

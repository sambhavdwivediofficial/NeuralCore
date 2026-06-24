// frontend/app/workflows/page.jsx

'use client';

import '@/styles/workflows.css';
import { useState } from 'react';
import Link from 'next/link';
import { GitBranch, Plus, Search } from 'lucide-react';
import { WorkflowCard } from '@/components/workflows/WorkflowCard';
import { EmptyState } from '@/components/common/EmptyState';
import { Loader } from '@/components/common/Loader';
import { SearchBar } from '@/components/common/SearchBar';
import { useWorkflows } from '@/hooks/useWorkflows';
import { ROUTES } from '@/lib/routes';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export default function WorkflowsPage() {
  const { workflows, isLoading, error, remove } = useWorkflows();
  const [search, setSearch] = useState('');

  const filtered = workflows.filter((w) =>
    w.name.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-lg font-semibold text-foreground">Workflows</h1>
          <p className="text-xs text-muted-foreground">{workflows.length} pipeline{workflows.length !== 1 ? 's' : ''} defined</p>
        </div>
        <div className="flex items-center gap-3">
          <SearchBar value={search} onChange={setSearch} placeholder="Search workflows…" className="w-56" />
          <Link href={ROUTES.WORKFLOW_CREATE}
            className="flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
            <Plus className="h-3.5 w-3.5" /> New workflow
          </Link>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title={search ? 'No workflows match your search' : 'No workflows yet'}
          description={search ? 'Try a different search term.' : 'Create your first workflow pipeline.'}
          action={!search ? { label: 'New workflow', href: ROUTES.WORKFLOW_CREATE } : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((wf) => (
            <Link key={wf.id} href={ROUTES.WORKFLOW(wf.id)}>
              <WorkflowCard
                workflow={wf}
                onDelete={async (id) => {
                  try { await remove(id); } catch (err) { toast.error(getErrorMessage(err)); }
                }}
              />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

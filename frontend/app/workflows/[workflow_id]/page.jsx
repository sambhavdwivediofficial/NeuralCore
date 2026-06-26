// frontend/app/workflows/[workflow_id]/page.jsx

'use client';

import '@/styles/workflows.css';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Play, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { WorkflowCanvas } from '@/components/workflows/WorkflowCanvas';
import { Tabs } from '@/components/common/Tabs';
import { Button } from '@/components/common/Button';
import { PageLoader as Loader } from '@/components/common/Loader';
import { useWorkflow } from '@/hooks/useWorkflows';
import { ROUTES } from '@/lib/routes';
import { cn } from '@/lib/utils';

const RUN_STATUS_CONFIG = {
  completed: { icon: CheckCircle2, class: 'text-success' },
  failed: { icon: XCircle, class: 'text-destructive' },
  running: { icon: Loader2, class: 'text-primary animate-spin' },
  started: { icon: Loader2, class: 'text-primary animate-spin' },
};

const TABS = [
  { id: 'canvas', label: 'Canvas' },
  { id: 'runs', label: 'Run history' },
];

export default function WorkflowDetailPage() {
  const { workflow_id } = useParams();
  const { workflow, runs, isLoading, runLoading, run } = useWorkflow(workflow_id);

  const [activeTab, setActiveTab] = useState('canvas');

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (!workflow) return <div className="p-6 text-sm text-muted-foreground">Workflow not found.</div>;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href={ROUTES.WORKFLOWS}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex flex-col">
            <h1 className="text-base font-semibold text-foreground">{workflow.name}</h1>
            <p className="text-xs text-muted-foreground capitalize">{workflow.template ?? 'custom'} · {runs.length} runs</p>
          </div>
        </div>
        <Button onClick={() => run({})} isLoading={runLoading} className="gap-1.5 self-start sm:self-auto">
          <Play className="h-3.5 w-3.5" /> Run workflow
        </Button>
      </div>

      <Tabs tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'canvas' && (
        <WorkflowCanvas />
      )}

      {activeTab === 'runs' && (
        <div className="flex flex-col gap-2">
          {runs.length === 0 ? (
            <div className="rounded-lg border border-border bg-card p-8 text-center">
              <p className="text-sm text-muted-foreground">No runs yet. Click &ldquo;Run workflow&rdquo; to start.</p>
            </div>
          ) : (
            runs.map((r) => {
              const conf = RUN_STATUS_CONFIG[r.status] ?? {};
              const Icon = conf.icon ?? Clock;
              return (
                <div key={r.id} className="workflow-step-row justify-between">
                  <div className="flex items-center gap-2.5">
                    <Icon className={cn('h-4 w-4 flex-shrink-0', conf.class)} />
                    <span className="text-xs font-mono text-muted-foreground">{r.id?.slice(0, 8)}…</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="capitalize">{r.status}</span>
                    {r.created_at && <span>{new Date(r.created_at).toLocaleString()}</span>}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

import { useState } from 'react';

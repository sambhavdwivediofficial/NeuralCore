// app/agents/page.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Bot } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { SearchBar } from '@/components/common/SearchBar';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonCard } from '@/components/common/Loader';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from '@/components/common/Modal';
import { AgentCard } from '@/components/agents/AgentCard';
import { useAgents } from '@/hooks/useAgents';
import { useProjectContext } from '@/context/ProjectContext';
import { deleteAgent, runAgent } from '@/services/agents';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { AGENT_TYPES, AGENT_TYPE_LABELS } from '@/lib/constants';
import '@/styles/dashboard.css';

export default function AgentsPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const { agents, isLoading, refresh } = useAgents({
    project_id: activeProjectId,
    search,
    type: typeFilter === 'all' ? undefined : typeFilter,
  });
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteAgent(deleteTarget.id);
      toast.success(`${deleteTarget.name} deleted`);
      setDeleteTarget(null);
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRun = async (agent) => {
    try {
      await runAgent(agent.id, { input: '' });
      toast.success(`${agent.name} started`);
      router.push(ROUTES.AGENT_DETAIL(agent.id));
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Agents</h1>
            <p className="text-sm text-muted-foreground">
              Configure and run autonomous agents for retrieval, research, and coding
            </p>
          </div>
          <Button onClick={() => router.push(ROUTES.AGENT_CREATE)}>
            <Plus className="h-3.5 w-3.5" />
            New agent
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <SearchBar value={search} onChange={setSearch} placeholder="Search agents" className="max-w-sm" />
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {Object.values(AGENT_TYPES).map((type) => (
                <SelectItem key={type} value={type}>
                  {AGENT_TYPE_LABELS[type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="dashboard-grid">
            {Array.from({ length: 6 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        ) : agents.length === 0 ? (
          <EmptyState
            icon={Bot}
            title="No agents yet"
            description="Create an agent to automate retrieval, research, coding, or orchestration tasks."
            action={
              <Button onClick={() => router.push(ROUTES.AGENT_CREATE)}>
                <Plus className="h-3.5 w-3.5" />
                New agent
              </Button>
            }
          />
        ) : (
          <div className="dashboard-grid">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onOpen={(a) => router.push(ROUTES.AGENT_DETAIL(a.id))}
                onRun={handleRun}
                onSettings={(a) => router.push(ROUTES.AGENT_SETTINGS(a.id))}
                onDelete={setDeleteTarget}
              />
            ))}
          </div>
        )}
      </div>

      <Modal open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Delete agent</ModalTitle>
            <ModalDescription>
              This will permanently delete &quot;{deleteTarget?.name}&quot; and its run history. This
              action cannot be undone.
            </ModalDescription>
          </ModalHeader>
          <ModalFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isDeleting} onClick={handleDelete}>
              Delete agent
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}

// app/projects/[project_id]/page.jsx

'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Bot,
  Database,
  Settings,
  BarChart3,
  Plus,
  ExternalLink,
} from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { PageLoader } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { useProject } from '@/hooks/useProjects';
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { useAgents } from '@/hooks/useAgents';
import { ROUTES } from '@/lib/routes';
import { LLM_PROVIDER_LABELS, AGENT_TYPE_LABELS, AGENT_STATUS } from '@/lib/constants';
import { formatRelativeTime, formatCompactNumber } from '@/lib/utils';
import '@/styles/dashboard.css';

const AGENT_STATUS_VARIANT = {
  [AGENT_STATUS.RUNNING]: 'default',
  [AGENT_STATUS.COMPLETED]: 'success',
  [AGENT_STATUS.FAILED]: 'destructive',
  [AGENT_STATUS.PAUSED]: 'warning',
  [AGENT_STATUS.IDLE]: 'muted',
};

export default function ProjectDetailPage({ params }) {
  const router = useRouter();

  // FIX: Unwrap params Promise using React.use()
  const { project_id } = use(params);

  const { project, isLoading } = useProject(project_id);
  const { knowledgeBases, isLoading: kbLoading } = useKnowledgeBases({
    project_id: project_id,
    page_size: 4,
  });
  const { agents, isLoading: agentsLoading } = useAgents({
    project_id: project_id,
    page_size: 4,
  });

  if (isLoading) {
    return (
      <AppShell>
        <PageLoader label="Loading project" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="-ml-2 w-fit"
              onClick={() => router.push(ROUTES.PROJECTS)}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Projects
            </Button>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">{project?.name}</h1>
              <p className="text-sm text-muted-foreground">
                {project?.description || 'No description provided'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="muted">
                {LLM_PROVIDER_LABELS[project?.default_llm_provider] || project?.default_llm_provider}
              </Badge>
              <span className="text-xs text-muted-foreground">
                Created {formatRelativeTime(project?.created_at)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(ROUTES.PROJECT_ANALYTICS(project_id))}
            >
              <BarChart3 className="h-3.5 w-3.5" />
              Analytics
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(ROUTES.PROJECT_SETTINGS(project_id))}
            >
              <Settings className="h-3.5 w-3.5" />
              Settings
            </Button>
          </div>
        </div>

        <div className="dashboard-chart-section">
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <div>
                <CardTitle>Knowledge bases</CardTitle>
                <CardDescription>Document collections available to this project</CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_CREATE)}>
                <Plus className="h-3.5 w-3.5" />
                New
              </Button>
            </CardHeader>
            <CardContent>
              {kbLoading ? (
                <div className="flex flex-col gap-2">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <div key={index} className="skeleton h-12 w-full rounded-md" />
                  ))}
                </div>
              ) : knowledgeBases.length === 0 ? (
                <EmptyState
                  icon={Database}
                  title="No knowledge bases"
                  description="Create a knowledge base to start ingesting documents."
                  action={
                    <Button size="sm" onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_CREATE)}>
                      <Plus className="h-3.5 w-3.5" />
                      New knowledge base
                    </Button>
                  }
                />
              ) : (
                <div className="flex flex-col divide-y divide-border">
                  {knowledgeBases.map((kb) => (
                    <button
                      key={kb.id}
                      onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_DETAIL(kb.id))}
                      className="interactive-row flex items-center justify-between rounded-md px-2 py-2.5 text-left"
                    >
                      <div className="flex flex-col gap-0.5">
                        <span className="text-sm font-medium text-foreground">{kb.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatCompactNumber(kb.document_count)} documents ·{' '}
                          {formatCompactNumber(kb.chunk_count)} chunks
                        </span>
                      </div>
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <div>
                <CardTitle>Agents</CardTitle>
                <CardDescription>Automated workflows configured for this project</CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={() => router.push(ROUTES.AGENT_CREATE)}>
                <Plus className="h-3.5 w-3.5" />
                New
              </Button>
            </CardHeader>
            <CardContent>
              {agentsLoading ? (
                <div className="flex flex-col gap-2">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <div key={index} className="skeleton h-12 w-full rounded-md" />
                  ))}
                </div>
              ) : agents.length === 0 ? (
                <EmptyState
                  icon={Bot}
                  title="No agents"
                  description="Create an agent to automate retrieval, research, or coding tasks."
                  action={
                    <Button size="sm" onClick={() => router.push(ROUTES.AGENT_CREATE)}>
                      <Plus className="h-3.5 w-3.5" />
                      New agent
                    </Button>
                  }
                />
              ) : (
                <div className="flex flex-col divide-y divide-border">
                  {agents.map((agent) => (
                    <button
                      key={agent.id}
                      onClick={() => router.push(ROUTES.AGENT_DETAIL(agent.id))}
                      className="interactive-row flex items-center justify-between rounded-md px-2 py-2.5 text-left"
                    >
                      <div className="flex flex-col gap-0.5">
                        <span className="text-sm font-medium text-foreground">{agent.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {AGENT_TYPE_LABELS[agent.type] || agent.type}
                        </span>
                      </div>
                      <Badge variant={AGENT_STATUS_VARIANT[agent.status] || 'muted'}>
                        {agent.status}
                      </Badge>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

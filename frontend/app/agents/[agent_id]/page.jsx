// app/agents/[agent_id]/page.jsx

'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Settings, History } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { PageLoader } from '@/components/common/Loader';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/common/Tabs';
import { AgentRunner } from '@/components/agents/AgentRunner';
import { AgentLogs } from '@/components/agents/AgentLogs';
import { useAgent, useAgentRuns } from '@/hooks/useAgents';
import { getAgentLogs } from '@/services/agents';
import { ROUTES } from '@/lib/routes';
import { AGENT_TYPE_LABELS, AGENT_STATUS } from '@/lib/constants';
import { formatRelativeTime } from '@/lib/utils';
import '@/styles/agents.css';

const STATUS_VARIANT = {
  [AGENT_STATUS.RUNNING]: 'default',
  [AGENT_STATUS.COMPLETED]: 'success',
  [AGENT_STATUS.FAILED]: 'destructive',
  [AGENT_STATUS.PAUSED]: 'warning',
  [AGENT_STATUS.IDLE]: 'muted',
};

const RESERVED_AGENT_IDS = ['create', 'new', 'edit', 'settings', 'delete'];

export default function AgentDetailPage({ params }) {
  const router = useRouter();
  const { agent_id } = use(params);

  if (RESERVED_AGENT_IDS.includes(agent_id)) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <h1 className="text-lg font-semibold">Invalid agent ID</h1>
          <p className="text-sm text-muted-foreground">
            &quot;{agent_id}&quot; is a reserved word and cannot be used as an agent ID.
          </p>
          <Button onClick={() => router.push(ROUTES.AGENTS)}>
            Back to Agents
          </Button>
        </div>
      </AppShell>
    );
  }

  const { agent, isLoading } = useAgent(agent_id);
  const { runs, isLoading: runsLoading } = useAgentRuns(agent_id, { page_size: 10 });
  const [selectedRunLogs, setSelectedRunLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);

  useEffect(() => {
    if (runs.length === 0) return;
    setLogsLoading(true);
    getAgentLogs(agent_id, runs[0].id, { page_size: 100 })
      .then((data) => setSelectedRunLogs(data?.items || []))
      .catch(() => setSelectedRunLogs([]))
      .finally(() => setLogsLoading(false));
  }, [runs, agent_id]);

  if (isLoading) {
    return (
      <AppShell>
        <PageLoader label="Loading agent" />
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
              onClick={() => router.push(ROUTES.AGENTS)}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Agents
            </Button>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold tracking-tight text-foreground">{agent?.name}</h1>
              <Badge variant={STATUS_VARIANT[agent?.status] || 'muted'}>{agent?.status}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {AGENT_TYPE_LABELS[agent?.type] || agent?.type} ·{' '}
              {agent?.description || 'No description provided'}
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push(ROUTES.AGENT_SETTINGS(agent_id))}
          >
            <Settings className="h-3.5 w-3.5" />
            Settings
          </Button>
        </div>

        <Tabs defaultValue="run">
          <TabsList>
            <TabsTrigger value="run">Run agent</TabsTrigger>
            <TabsTrigger value="history">Run history</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
          </TabsList>

          <TabsContent value="run">
            <Card>
              <CardContent className="p-4">
                <AgentRunner agentId={agent_id} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history">
            <Card>
              <CardHeader>
                <CardTitle>Run history</CardTitle>
                <CardDescription>Recent executions of this agent</CardDescription>
              </CardHeader>
              <CardContent>
                {runsLoading ? (
                  <div className="flex flex-col gap-2">
                    {Array.from({ length: 4 }).map((_, index) => (
                      <div key={index} className="skeleton h-12 w-full rounded-md" />
                    ))}
                  </div>
                ) : runs.length === 0 ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    <History className="mx-auto mb-2 h-5 w-5" />
                    No runs yet
                  </div>
                ) : (
                  <div className="flex flex-col divide-y divide-border">
                    {runs.map((run) => (
                      <div key={run.id} className="flex items-center justify-between py-2.5">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-sm text-foreground">
                            {run.input_summary || 'No input summary'}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(run.started_at)}
                          </span>
                        </div>
                        <Badge variant={STATUS_VARIANT[run.status] || 'muted'}>{run.status}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="logs">
            <AgentLogs logs={selectedRunLogs} isLoading={logsLoading} />
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  );
}

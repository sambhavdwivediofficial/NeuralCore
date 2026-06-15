// app/dashboard/page.jsx

'use client';

import { useRouter } from 'next/navigation';
import {
  Activity,
  Bot,
  Database,
  DollarSign,
  Plus,
  Upload,
  SearchCode,
} from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { UsageGraph } from '@/components/dashboard/UsageGraph';
import { CostChart } from '@/components/dashboard/CostChart';
import { ActivityChart } from '@/components/dashboard/ActivityChart';
import { useProjectContext } from '@/context/ProjectContext';
import { useProjectAnalytics } from '@/hooks/useProjects';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/common/DropdownMenu';
import { ROUTES } from '@/lib/routes';
import { formatCompactNumber, formatCurrency, formatMs } from '@/lib/utils';
import '@/styles/dashboard.css';

export default function DashboardPage() {
  const router = useRouter();
  const { activeProject, activeProjectId, isLoading: projectsLoading } = useProjectContext();
  const { analytics, isLoading } = useProjectAnalytics(activeProjectId, { range: '7d' });

  const loading = projectsLoading || isLoading;

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-0">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">
              {activeProject?.name || 'Dashboard'}
            </h1>
            <p className="text-sm text-muted-foreground">
              Overview of usage, costs, and activity for this project
            </p>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm">
                <Plus className="h-3.5 w-3.5" />
                Quick actions
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_CREATE)}>
                <Upload className="h-3.5 w-3.5" />
                Upload documents
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push(ROUTES.AGENT_CREATE)}>
                <Bot className="h-3.5 w-3.5" />
                Create agent
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push(ROUTES.RETRIEVAL_DEBUGGER)}>
                <SearchCode className="h-3.5 w-3.5" />
                Test retrieval
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="dashboard-grid">
          <StatsCard
            label="Total requests"
            value={formatCompactNumber(analytics?.total_requests)}
            change={analytics?.requests_change}
            changeLabel="vs last week"
            icon={Activity}
            isLoading={loading}
          />
          <StatsCard
            label="Active agents"
            value={formatCompactNumber(analytics?.active_agents)}
            change={analytics?.agents_change}
            changeLabel="vs last week"
            icon={Bot}
            isLoading={loading}
          />
          <StatsCard
            label="Documents indexed"
            value={formatCompactNumber(analytics?.documents_indexed)}
            change={analytics?.documents_change}
            changeLabel="vs last week"
            icon={Database}
            isLoading={loading}
          />
          <StatsCard
            label="Estimated cost"
            value={formatCurrency(analytics?.total_cost)}
            change={analytics?.cost_change}
            changeLabel="vs last week"
            icon={DollarSign}
            isLoading={loading}
          />
        </div>

        <div className="dashboard-chart-section">
          <UsageGraph
            data={analytics?.usage_series}
            isLoading={loading}
            description="Requests processed over the last 7 days"
          />
          <CostChart
            data={analytics?.cost_by_model}
            isLoading={loading}
            description="Spend distribution by model"
          />
        </div>

        <div className="dashboard-chart-section">
          <ActivityChart
            items={analytics?.recent_activity}
            isLoading={loading}
            description="Latest events across this project"
          />
          <div className="card-surface flex flex-col gap-3 p-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Performance snapshot</h3>
              <p className="text-xs text-muted-foreground">Average response characteristics</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="metric-tile">
                <span className="metric-tile-label">Avg latency</span>
                <span className="metric-tile-value">{formatMs(analytics?.avg_latency_ms)}</span>
              </div>
              <div className="metric-tile">
                <span className="metric-tile-label">p95 latency</span>
                <span className="metric-tile-value">{formatMs(analytics?.p95_latency_ms)}</span>
              </div>
              <div className="metric-tile">
                <span className="metric-tile-label">Retrieval hit rate</span>
                <span className="metric-tile-value">
                  {analytics?.retrieval_hit_rate
                    ? `${(analytics.retrieval_hit_rate * 100).toFixed(1)}%`
                    : '--'}
                </span>
              </div>
              <div className="metric-tile">
                <span className="metric-tile-label">Cache hit rate</span>
                <span className="metric-tile-value">
                  {analytics?.cache_hit_rate
                    ? `${(analytics.cache_hit_rate * 100).toFixed(1)}%`
                    : '--'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

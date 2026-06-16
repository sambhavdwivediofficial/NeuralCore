// app/projects/[project_id]/analytics.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Download, Activity, DollarSign, Gauge, Database } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { PageLoader } from '@/components/common/Loader';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { UsageGraph } from '@/components/dashboard/UsageGraph';
import { CostChart } from '@/components/dashboard/CostChart';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { useProject, useProjectAnalytics } from '@/hooks/useProjects';
import { ROUTES } from '@/lib/routes';
import { formatCompactNumber, formatCurrency, formatMs, downloadJson } from '@/lib/utils';
import '@/styles/dashboard.css';

const RANGE_OPTIONS = [
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
];

export default function ProjectAnalyticsPage({ params }) {
  const router = useRouter();
  const [range, setRange] = useState('7d');
  const { project, isLoading: projectLoading } = useProject(params.project_id);
  const { analytics, isLoading } = useProjectAnalytics(params.project_id, { range });

  if (projectLoading) {
    return (
      <AppShell>
        <PageLoader label="Loading analytics" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="-ml-2 w-fit"
              onClick={() => router.push(ROUTES.PROJECT_DETAIL(params.project_id))}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              {project?.name}
            </Button>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">Analytics</h1>
              <p className="text-sm text-muted-foreground">
                Usage, cost, and performance trends for this project
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Select value={range} onValueChange={setRange}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RANGE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadJson(analytics, `analytics-${params.project_id}.json`)}
            >
              <Download className="h-3.5 w-3.5" />
              Export
            </Button>
          </div>
        </div>

        <div className="dashboard-grid">
          <StatsCard
            label="Total requests"
            value={formatCompactNumber(analytics?.total_requests)}
            change={analytics?.requests_change}
            changeLabel={`vs previous ${range}`}
            icon={Activity}
            isLoading={isLoading}
          />
          <StatsCard
            label="Total cost"
            value={formatCurrency(analytics?.total_cost)}
            change={analytics?.cost_change}
            changeLabel={`vs previous ${range}`}
            icon={DollarSign}
            isLoading={isLoading}
          />
          <StatsCard
            label="Avg latency"
            value={formatMs(analytics?.avg_latency_ms)}
            change={analytics?.latency_change}
            changeLabel={`vs previous ${range}`}
            icon={Gauge}
            isLoading={isLoading}
          />
          <StatsCard
            label="Documents indexed"
            value={formatCompactNumber(analytics?.documents_indexed)}
            change={analytics?.documents_change}
            changeLabel={`vs previous ${range}`}
            icon={Database}
            isLoading={isLoading}
          />
        </div>

        <div className="dashboard-chart-section">
          <UsageGraph
            data={analytics?.usage_series}
            isLoading={isLoading}
            description={`Request volume over ${range}`}
          />
          <CostChart
            data={analytics?.cost_by_model}
            isLoading={isLoading}
            description="Spend distribution by model"
          />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Retrieval quality</CardTitle>
            <CardDescription>Aggregate metrics across all retrieval queries</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="metric-tile">
              <span className="metric-tile-label">Hit rate</span>
              <span className="metric-tile-value">
                {analytics?.retrieval_hit_rate
                  ? `${(analytics.retrieval_hit_rate * 100).toFixed(1)}%`
                  : '--'}
              </span>
            </div>
            <div className="metric-tile">
              <span className="metric-tile-label">Avg NDCG@10</span>
              <span className="metric-tile-value">
                {analytics?.avg_ndcg ? analytics.avg_ndcg.toFixed(3) : '--'}
              </span>
            </div>
            <div className="metric-tile">
              <span className="metric-tile-label">Avg MRR</span>
              <span className="metric-tile-value">
                {analytics?.avg_mrr ? analytics.avg_mrr.toFixed(3) : '--'}
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
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

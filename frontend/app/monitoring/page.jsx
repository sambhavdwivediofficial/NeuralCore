// app/monitoring/page.jsx

'use client';

import { useRouter } from 'next/navigation';
import { ScrollText, GitBranch, Bell, ChevronRight } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { SkeletonCard } from '@/components/common/Loader';
import { useSystemHealth, useMetricsOverview } from '@/hooks/useMonitoring';
import { ROUTES } from '@/lib/routes';
import { formatMs, formatCompactNumber, formatPercent } from '@/lib/utils';
import '@/styles/dashboard.css';

export default function MonitoringPage() {
  const router = useRouter();
  const { health, isLoading: healthLoading } = useSystemHealth();
  const { metrics, isLoading: metricsLoading } = useMetricsOverview({ range: '1h' });

  const services = health?.services || [];

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Monitoring</h1>
          <p className="text-sm text-muted-foreground">
            System health, performance metrics, and observability tools
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <button
            onClick={() => router.push(ROUTES.MONITORING_LOGS)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <ScrollText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Logs</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => router.push(ROUTES.MONITORING_TRACES)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <GitBranch className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Traces</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => router.push(ROUTES.MONITORING_ALERTS)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <Bell className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Alerts</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Service health</CardTitle>
            <CardDescription>Status of core infrastructure components</CardDescription>
          </CardHeader>
          <CardContent>
            {healthLoading ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Array.from({ length: 4 }).map((_, index) => (
                  <SkeletonCard key={index} className="h-16" />
                ))}
              </div>
            ) : services.length === 0 ? (
              <p className="text-sm text-muted-foreground">No service data available</p>
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {services.map((service) => (
                  <div key={service.name} className="metric-tile">
                    <div className="flex items-center justify-between">
                      <span className="metric-tile-label">{service.name}</span>
                      <span
                        className={`status-dot ${service.healthy ? 'bg-success' : 'bg-destructive'}`}
                      />
                    </div>
                    <span className="metric-tile-value">{service.healthy ? 'Healthy' : 'Down'}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Performance overview</CardTitle>
            <CardDescription>Aggregate metrics for the last hour</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="metric-tile">
              <span className="metric-tile-label">Requests/min</span>
              <span className="metric-tile-value">
                {metricsLoading ? '--' : formatCompactNumber(metrics?.requests_per_minute)}
              </span>
            </div>
            <div className="metric-tile">
              <span className="metric-tile-label">p95 latency</span>
              <span className="metric-tile-value">
                {metricsLoading ? '--' : formatMs(metrics?.p95_latency_ms)}
              </span>
            </div>
            <div className="metric-tile">
              <span className="metric-tile-label">Error rate</span>
              <span className="metric-tile-value">
                {metricsLoading ? '--' : formatPercent(metrics?.error_rate)}
              </span>
            </div>
            <div className="metric-tile">
              <span className="metric-tile-label">Active connections</span>
              <span className="metric-tile-value">
                {metricsLoading ? '--' : formatCompactNumber(metrics?.active_connections)}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

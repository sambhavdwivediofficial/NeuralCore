// app/retrieval-debugger/metrics.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { UsageGraph } from '@/components/dashboard/UsageGraph';
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { useProjectContext } from '@/context/ProjectContext';
import { useRetrievalMetrics } from '@/hooks/useRetrieval';
import { ROUTES } from '@/lib/routes';
import { formatMs } from '@/lib/utils';
import '@/styles/retrieval.css';

export default function RetrievalMetricsPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const { knowledgeBases } = useKnowledgeBases({ project_id: activeProjectId });
  const [kbId, setKbId] = useState('');
  const { metrics, isLoading } = useRetrievalMetrics(kbId, { range: '7d' });

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.RETRIEVAL_DEBUGGER)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Retrieval debugger
        </Button>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Retrieval metrics</h1>
            <p className="text-sm text-muted-foreground">
              Quality and performance metrics aggregated across queries
            </p>
          </div>
          <Select value={kbId} onValueChange={setKbId}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Select knowledge base" />
            </SelectTrigger>
            <SelectContent>
              {knowledgeBases.map((kb) => (
                <SelectItem key={kb.id} value={kb.id}>
                  {kb.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {!kbId ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            Select a knowledge base to view its retrieval metrics
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="metric-tile">
                <span className="metric-tile-label">Avg NDCG@10</span>
                <span className="metric-tile-value">
                  {isLoading ? '--' : metrics?.avg_ndcg?.toFixed(3) ?? '--'}
                </span>
              </div>
              <div className="metric-tile">
                <span className="metric-tile-label">Avg MRR</span>
                <span className="metric-tile-value">
                  {isLoading ? '--' : metrics?.avg_mrr?.toFixed(3) ?? '--'}
                </span>
              </div>
              <div className="metric-tile">
                <span className="metric-tile-label">Avg precision@5</span>
                <span className="metric-tile-value">
                  {isLoading ? '--' : metrics?.avg_precision_at_5?.toFixed(3) ?? '--'}
                </span>
              </div>
              <div className="metric-tile">
                <span className="metric-tile-label">Avg latency</span>
                <span className="metric-tile-value">
                  {isLoading ? '--' : formatMs(metrics?.avg_latency_ms)}
                </span>
              </div>
            </div>

            <UsageGraph
              data={metrics?.query_volume_series}
              isLoading={isLoading}
              title="Query volume"
              description="Retrieval queries executed over time"
            />

            <Card>
              <CardHeader>
                <CardTitle>Strategy breakdown</CardTitle>
                <CardDescription>Query volume by retrieval strategy used</CardDescription>
              </CardHeader>
              <CardContent>
                {!metrics?.strategy_breakdown || metrics.strategy_breakdown.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No data available yet</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {metrics.strategy_breakdown.map((item) => (
                      <div key={item.strategy} className="flex items-center justify-between text-sm">
                        <span className="capitalize text-foreground">{item.strategy}</span>
                        <span className="text-muted-foreground">{item.count} queries</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}

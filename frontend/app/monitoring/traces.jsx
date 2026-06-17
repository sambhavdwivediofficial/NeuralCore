// app/monitoring/traces.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, GitBranch } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonTable } from '@/components/common/Loader';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
} from '@/components/common/Modal';
import { useTraces } from '@/hooks/useMonitoring';
import { ROUTES } from '@/lib/routes';
import { formatMs, formatRelativeTime } from '@/lib/utils';

export default function MonitoringTracesPage() {
  const router = useRouter();
  const { traces, isLoading } = useTraces({ page_size: 50 });
  const [selectedTrace, setSelectedTrace] = useState(null);

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.MONITORING)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Monitoring
        </Button>

        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Traces</h1>
          <p className="text-sm text-muted-foreground">
            Distributed request traces across retrieval, agents, and model calls
          </p>
        </div>

        {isLoading ? (
          <SkeletonTable rows={8} columns={4} />
        ) : traces.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title="No traces found"
            description="Traces will appear here once requests are sampled."
          />
        ) : (
          <div className="flex flex-col gap-2">
            {traces.map((trace) => (
              <button
                key={trace.id}
                onClick={() => setSelectedTrace(trace)}
                className="card-surface interactive-row flex items-center justify-between p-3 text-left"
              >
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium text-foreground">{trace.operation_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {trace.span_count} spans · {formatRelativeTime(trace.started_at)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={trace.has_error ? 'destructive' : 'success'}>
                    {trace.has_error ? 'Error' : 'OK'}
                  </Badge>
                  <span className="text-xs font-medium text-foreground">
                    {formatMs(trace.duration_ms)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <Modal open={Boolean(selectedTrace)} onOpenChange={(open) => !open && setSelectedTrace(null)}>
        <ModalContent className="max-w-2xl">
          <ModalHeader>
            <ModalTitle>{selectedTrace?.operation_name}</ModalTitle>
            <ModalDescription>
              Trace ID: {selectedTrace?.id} · {formatMs(selectedTrace?.duration_ms)}
            </ModalDescription>
          </ModalHeader>
          <Card>
            <CardContent className="scrollbar-thin max-h-80 overflow-y-auto p-3">
              {(selectedTrace?.spans || []).map((span) => (
                <div
                  key={span.id}
                  className="flex items-center justify-between border-b border-border py-2 text-sm last:border-none"
                  style={{ paddingLeft: `${(span.depth || 0) * 16}px` }}
                >
                  <span className="text-foreground">{span.name}</span>
                  <span className="text-xs text-muted-foreground">{formatMs(span.duration_ms)}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}

// app/monitoring/logs.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ScrollText } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { SearchBar } from '@/components/common/SearchBar';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonText } from '@/components/common/Loader';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { useLogs } from '@/hooks/useMonitoring';
import { ROUTES } from '@/lib/routes';
import { LOG_LEVELS, LOG_LEVEL_COLORS, DATE_FORMATS } from '@/lib/constants';
import { formatDate, cn } from '@/lib/utils';
import '@/styles/agents.css';

export default function MonitoringLogsPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [level, setLevel] = useState('all');
  const { logs, isLoading } = useLogs({
    search,
    level: level === 'all' ? undefined : level,
    page_size: 100,
  });

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
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Logs</h1>
          <p className="text-sm text-muted-foreground">
            Structured application logs across all backend services
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <SearchBar value={search} onChange={setSearch} placeholder="Search logs" className="max-w-sm" />
          <Select value={level} onValueChange={setLevel}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All levels</SelectItem>
              {Object.values(LOG_LEVELS).map((value) => (
                <SelectItem key={value} value={value} className="capitalize">
                  {value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="card-surface p-4">
            <SkeletonText lines={10} />
          </div>
        ) : logs.length === 0 ? (
          <EmptyState
            icon={ScrollText}
            title="No logs found"
            description="Try adjusting your search or level filter."
          />
        ) : (
          <div className="card-surface scrollbar-thin max-h-[36rem] overflow-y-auto p-3">
            {logs.map((log) => (
              <div key={log.id} className="agent-log-line">
                <span className="agent-log-timestamp">
                  {formatDate(log.timestamp, DATE_FORMATS.LONG)}
                </span>
                <span className={cn(LOG_LEVEL_COLORS[log.level] || 'text-foreground')}>
                  <span className="mr-2 text-2xs font-semibold uppercase">{log.level}</span>
                  <span className="mr-2 text-2xs text-muted-foreground">[{log.service}]</span>
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

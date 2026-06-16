// components/agents/AgentLogs.jsx

import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonText } from '@/components/common/Loader';
import { ScrollText } from 'lucide-react';
import { LOG_LEVEL_COLORS, DATE_FORMATS } from '@/lib/constants';
import { formatDate, cn } from '@/lib/utils';
import '@/styles/agents.css';

export function AgentLogs({ logs, isLoading }) {
  if (isLoading) {
    return (
      <div className="card-surface p-4">
        <SkeletonText lines={6} />
      </div>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <EmptyState
        icon={ScrollText}
        title="No logs yet"
        description="Logs will appear here once the agent starts running."
      />
    );
  }

  return (
    <div className="card-surface scrollbar-thin max-h-96 overflow-y-auto p-3">
      {logs.map((log) => (
        <div key={log.id} className="agent-log-line">
          <span className="agent-log-timestamp">{formatDate(log.timestamp, DATE_FORMATS.TIME)}</span>
          <span className={cn(LOG_LEVEL_COLORS[log.level] || 'text-foreground')}>
            <span className="mr-2 text-2xs font-semibold uppercase">{log.level}</span>
            {log.message}
          </span>
        </div>
      ))}
    </div>
  );
}

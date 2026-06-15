// components/dashboard/ActivityChart.jsx

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/common/Card';
import { SkeletonText } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { History, Bot, Database, KeyRound, FolderPlus, AlertCircle } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

const EVENT_ICONS = {
  agent_run: Bot,
  document_upload: Database,
  api_key_created: KeyRound,
  project_created: FolderPlus,
  alert: AlertCircle,
  default: History,
};

export function ActivityChart({ items, isLoading, title = 'Recent activity', description }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <SkeletonText lines={5} />
        ) : !items || items.length === 0 ? (
          <EmptyState
            icon={History}
            title="No recent activity"
            description="Activity from agents, documents, and team members will show up here."
          />
        ) : (
          <div className="flex flex-col">
            {items.map((item) => {
              const Icon = EVENT_ICONS[item.type] || EVENT_ICONS.default;
              return (
                <div key={item.id} className="activity-feed-item pb-4 last:pb-0">
                  <div className="flex items-start gap-3">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex flex-1 flex-col gap-0.5">
                      <p className="text-sm text-foreground">{item.description}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.actor ? `${item.actor} · ` : ''}
                        {formatRelativeTime(item.created_at)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

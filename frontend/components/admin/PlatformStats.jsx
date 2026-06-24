// frontend/components/admin/PlatformStats.jsx

import { Building2, Users, Bot, Activity, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

const STAT_CONFIG = [
  { key: 'total_organizations', label: 'Organizations', icon: Building2, color: 'text-blue-500 bg-blue-500/10' },
  { key: 'total_users', label: 'Total Users', icon: Users, color: 'text-violet-500 bg-violet-500/10' },
  { key: 'total_agents', label: 'Agents', icon: Bot, color: 'text-emerald-500 bg-emerald-500/10' },
  { key: 'total_queries', label: 'Queries', icon: Activity, color: 'text-orange-500 bg-orange-500/10' },
];

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</span>
        <div className={cn('flex h-8 w-8 items-center justify-center rounded-md', color)}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <span className="text-2xl font-bold tracking-tight text-foreground font-mono">
        {typeof value === 'number' ? value.toLocaleString() : (value ?? '—')}
      </span>
    </div>
  );
}

export function PlatformStats({ stats, isLoading }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CONFIG.map((s) => (
          <div key={s.key} className="h-24 rounded-lg border border-border bg-card animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {STAT_CONFIG.map((s) => (
        <StatCard
          key={s.key}
          label={s.label}
          value={stats?.[s.key]}
          icon={s.icon}
          color={s.color}
        />
      ))}
    </div>
  );
}

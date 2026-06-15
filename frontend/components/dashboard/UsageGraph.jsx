// components/dashboard/UsageGraph.jsx

'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/common/Card';
import { SkeletonCard } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { Activity } from 'lucide-react';
import { formatCompactNumber, formatDate } from '@/lib/utils';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="dashboard-tooltip">
      <p className="dashboard-tooltip-label">{formatDate(label, 'MMM d')}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="dashboard-tooltip-value">
          {entry.name}: {formatCompactNumber(entry.value)}
        </p>
      ))}
    </div>
  );
}

export function UsageGraph({ data, isLoading, title = 'Request volume', description }) {
  if (isLoading) return <SkeletonCard className="h-72" />;

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={Activity}
            title="No usage data yet"
            description="Once your project starts receiving traffic, request volume will appear here."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className="h-64 pl-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="usageGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity={0.25} />
                <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => formatDate(value, 'MMM d')}
              tickLine={false}
              axisLine={false}
              minTickGap={24}
            />
            <YAxis
              tickFormatter={(value) => formatCompactNumber(value)}
              tickLine={false}
              axisLine={false}
              width={42}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="requests"
              name="Requests"
              stroke="hsl(var(--chart-1))"
              strokeWidth={2}
              fill="url(#usageGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

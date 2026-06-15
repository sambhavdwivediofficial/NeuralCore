// components/dashboard/CostChart.jsx

'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/common/Card';
import { SkeletonCard } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { Wallet } from 'lucide-react';
import { formatCurrency } from '@/lib/utils';
import { COLOR_PALETTE } from '@/lib/constants';

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const entry = payload[0];

  return (
    <div className="dashboard-tooltip">
      <p className="dashboard-tooltip-label">{entry.payload.name}</p>
      <p className="dashboard-tooltip-value">{formatCurrency(entry.value)}</p>
    </div>
  );
}

export function CostChart({ data, isLoading, title = 'Cost by model', description }) {
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
            icon={Wallet}
            title="No cost data yet"
            description="Cost breakdown by model and provider will appear once requests are processed."
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
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid horizontal={false} strokeDasharray="3 3" />
            <XAxis
              type="number"
              tickFormatter={(value) => formatCurrency(value)}
              tickLine={false}
              axisLine={false}
            />
            <YAxis type="category" dataKey="name" tickLine={false} axisLine={false} width={110} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--muted) / 0.4)' }} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={20}>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLOR_PALETTE[index % COLOR_PALETTE.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

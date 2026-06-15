// components/dashboard/StatsCard.jsx

import { ArrowDown, ArrowUp, Minus } from 'lucide-react';
import { Card, CardContent } from '@/components/common/Card';
import { cn } from '@/lib/utils';

export function StatsCard({ label, value, change, changeLabel, icon: Icon, isLoading }) {
  const isPositive = change > 0;
  const isNegative = change < 0;
  const isNeutral = !change;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">{label}</span>
          {Icon ? (
            <div className="stats-card-icon">
              <Icon className="h-4 w-4" />
            </div>
          ) : null}
        </div>

        {isLoading ? (
          <div className="skeleton h-7 w-24 rounded-md" />
        ) : (
          <span className="text-2xl font-semibold tracking-tight text-foreground">{value}</span>
        )}

        {change !== undefined && !isLoading ? (
          <div className="flex items-center gap-1.5 text-xs">
            <span
              className={cn(
                'flex items-center gap-0.5 font-medium',
                isPositive && 'text-success',
                isNegative && 'text-destructive',
                isNeutral && 'text-muted-foreground'
              )}
            >
              {isPositive ? (
                <ArrowUp className="h-3 w-3" />
              ) : isNegative ? (
                <ArrowDown className="h-3 w-3" />
              ) : (
                <Minus className="h-3 w-3" />
              )}
              {Math.abs(change)}%
            </span>
            <span className="text-muted-foreground">{changeLabel}</span>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

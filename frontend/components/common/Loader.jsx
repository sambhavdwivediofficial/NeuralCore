// components/common/Loader.jsx

import { cn } from '@/lib/utils';

export function Spinner({ className, size = 20 }) {
  return (
    <span
      className={cn('orbit-spinner', className)}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    >
      <span className="orbit-spinner-ring orbit-spinner-ring--outer" />
      <span className="orbit-spinner-ring orbit-spinner-ring--inner" />
    </span>
  );
}

export function PageLoader({ label = 'Loading' }) {
  return (
    <div className="flex h-full min-h-[80vh] w-full flex-col items-center justify-center gap-3">
      <Spinner size={66} />
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function Skeleton({ className }) {
  return <div className={cn('skeleton rounded-md', className)} />;
}

export function SkeletonText({ lines = 3, className }) {
  return (
    <div className={cn('flex flex-col gap-2', className)} data-testid="skeleton-text">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          className={cn('h-3', index === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className }) {
  return (
    <div className={cn('card-surface flex flex-col gap-3 p-4', className)} data-testid="skeleton-card">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4 rounded-full" />
      </div>
      <Skeleton className="h-7 w-20" />
      <Skeleton className="h-3 w-24" />
    </div>
  );
}

export function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div className="card-surface overflow-hidden" data-testid="skeleton-table">
      <div className="border-b border-border p-3">
        <div className="flex gap-4">
          {Array.from({ length: columns }).map((_, index) => (
            <Skeleton key={index} className="h-3 flex-1" />
          ))}
        </div>
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="p-3">
            <div className="flex gap-4">
              {Array.from({ length: columns }).map((__, colIndex) => (
                <Skeleton key={colIndex} className="h-3 flex-1" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function InlineLoader({ label }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Spinner size={16} />
      {label ? <span>{label}</span> : null}
    </div>
  );
}

export function OverlayLoader({ label = 'Loading', show = true }) {
  if (!show) return null;

  return (
    <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-background/70 backdrop-blur-sm">
      <Spinner size={32} />
      {label ? <p className="text-sm text-muted-foreground">{label}</p> : null}
    </div>
  );
}

export function ButtonSpinner({ className }) {
  return <Spinner size={14} className={cn('shrink-0', className)} />;
}

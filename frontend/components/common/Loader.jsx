// components/common/Loader.jsx

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Spinner({ className, size = 16 }) {
  return <Loader2 className={cn('animate-spin text-muted-foreground', className)} style={{ width: size, height: size }} />;
}

export function PageLoader({ label = 'Loading' }) {
  return (
    <div className="flex h-full min-h-[40vh] w-full flex-col items-center justify-center gap-3">
      <Spinner size={22} />
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function Skeleton({ className }) {
  return <div className={cn('skeleton rounded-md', className)} />;
}

export function SkeletonText({ lines = 3, className }) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
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
    <div className={cn('card-surface flex flex-col gap-3 p-4', className)}>
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
    <div className="card-surface overflow-hidden">
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
      <Spinner size={14} />
      {label ? <span>{label}</span> : null}
    </div>
  );
}

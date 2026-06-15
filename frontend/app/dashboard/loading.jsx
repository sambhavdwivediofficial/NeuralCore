// app/dashboard/loading.jsx

import { AppShell } from '@/components/layout/AppShell';
import { SkeletonCard, Skeleton } from '@/components/common/Loader';

export default function DashboardLoading() {
  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-8 w-28" />
        </div>
        <div className="dashboard-grid">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonCard key={index} />
          ))}
        </div>
        <div className="dashboard-chart-section">
          <Skeleton className="h-72 w-full rounded-lg" />
          <Skeleton className="h-72 w-full rounded-lg" />
        </div>
      </div>
    </AppShell>
  );
}

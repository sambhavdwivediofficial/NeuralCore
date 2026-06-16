// components/vectorstores/StoreMetrics.jsx

import { SkeletonCard } from '@/components/common/Loader';
import { formatCompactNumber, formatBytes, formatMs } from '@/lib/utils';

export function StoreMetrics({ metrics, isLoading }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonCard key={index} className="h-20" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div className="metric-tile">
        <span className="metric-tile-label">Total vectors</span>
        <span className="metric-tile-value">{formatCompactNumber(metrics?.total_vectors)}</span>
      </div>
      <div className="metric-tile">
        <span className="metric-tile-label">Collections</span>
        <span className="metric-tile-value">{formatCompactNumber(metrics?.collection_count)}</span>
      </div>
      <div className="metric-tile">
        <span className="metric-tile-label">Storage used</span>
        <span className="metric-tile-value">{formatBytes(metrics?.storage_bytes)}</span>
      </div>
      <div className="metric-tile">
        <span className="metric-tile-label">Avg query latency</span>
        <span className="metric-tile-value">{formatMs(metrics?.avg_query_latency_ms)}</span>
      </div>
    </div>
  );
}

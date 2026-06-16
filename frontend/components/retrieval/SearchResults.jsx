// components/retrieval/SearchResults.jsx

import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonText } from '@/components/common/Loader';
import { ScoreCard } from '@/components/retrieval/ScoreCard';
import { Badge } from '@/components/common/Badge';
import { SearchX } from 'lucide-react';
import '@/styles/retrieval.css';

export function SearchResults({ results, isLoading }) {
  if (isLoading) {
    return (
      <div className="card-surface p-4">
        <SkeletonText lines={6} />
      </div>
    );
  }

  if (!results || results.length === 0) {
    return (
      <EmptyState
        icon={SearchX}
        title="No results"
        description="Try a different query, strategy, or knowledge base."
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {results.map((item, index) => (
        <div key={item.chunk_id} className="retrieval-result-card">
          <div className="flex items-center justify-between">
            <Badge variant="muted" className="max-w-[14rem] truncate">
              {item.document_name}
            </Badge>
            {item.metadata?.source ? (
              <span className="text-2xs text-muted-foreground">{item.metadata.source}</span>
            ) : null}
          </div>
          <p className="text-sm leading-relaxed text-foreground">{item.content}</p>
          <ScoreCard rank={index + 1} score={item.score} />
        </div>
      ))}
    </div>
  );
}

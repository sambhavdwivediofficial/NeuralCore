// components/retrieval/RerankViewer.jsx

import { ArrowRight, ArrowUp, ArrowDown, Minus, ListOrdered } from 'lucide-react';
import { EmptyState } from '@/components/common/EmptyState';
import { truncate } from '@/lib/utils';
import '@/styles/retrieval.css';

function getDirection(before, after) {
  if (after < before) return 'up';
  if (after > before) return 'down';
  return 'same';
}

export function RerankViewer({ beforeResults, afterResults }) {
  if (!beforeResults || !afterResults || beforeResults.length === 0) {
    return (
      <EmptyState
        icon={ListOrdered}
        title="No reranking data"
        description="Run a query with reranking enabled to compare before and after ordering."
      />
    );
  }

  const afterPositionMap = new Map(afterResults.map((item, index) => [item.chunk_id, index]));

  return (
    <div className="flex flex-col gap-2">
      {beforeResults.map((item, beforeIndex) => {
        const afterIndex = afterPositionMap.get(item.chunk_id);
        const direction = afterIndex !== undefined ? getDirection(beforeIndex, afterIndex) : 'same';
        const DirectionIcon = direction === 'up' ? ArrowUp : direction === 'down' ? ArrowDown : Minus;

        return (
          <div key={item.chunk_id} className="rerank-comparison rounded-md border border-border p-3">
            <div className="flex items-center gap-2">
              <span className="retrieval-result-rank" data-rank={String(beforeIndex + 1)}>
                {beforeIndex + 1}
              </span>
              <span className="text-xs text-muted-foreground">{truncate(item.content, 60)}</span>
            </div>
            <div className="rerank-arrow">
              <ArrowRight className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-2">
              <span
                className="retrieval-result-rank"
                data-rank={String((afterIndex ?? beforeIndex) + 1)}
              >
                {(afterIndex ?? beforeIndex) + 1}
              </span>
              <span className="rerank-position-change" data-direction={direction}>
                <DirectionIcon className="h-3 w-3" />
                {afterIndex !== undefined ? Math.abs(afterIndex - beforeIndex) : 0}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

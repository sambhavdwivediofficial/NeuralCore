// components/retrieval/ScoreCard.jsx

import { classNamesByScore } from '@/lib/utils';
import '@/styles/retrieval.css';

export function ScoreCard({ rank, score, label = 'Relevance' }) {
  const tier = classNamesByScore(score);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {rank ? (
            <span className="retrieval-result-rank" data-rank={String(rank)}>
              {rank}
            </span>
          ) : null}
          <span className="text-2xs text-muted-foreground">{label}</span>
        </div>
        <span className="text-xs font-semibold text-foreground">{score.toFixed(4)}</span>
      </div>
      <div className="score-bar-track">
        <div
          className="score-bar-fill"
          data-tier={tier}
          style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
        />
      </div>
    </div>
  );
}

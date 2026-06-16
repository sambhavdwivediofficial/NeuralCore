// components/knowledge/EmbeddingViewer.jsx

'use client';

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/common/Card';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonCard } from '@/components/common/Loader';
import { Sigma } from 'lucide-react';
import { formatCompactNumber } from '@/lib/utils';
import '@/styles/knowledge.css';

function valueToColor(value) {
  const intensity = Math.min(1, Math.abs(value));
  if (value >= 0) {
    return `hsl(243, 75%, ${60 - intensity * 25}%)`;
  }
  return `hsl(0, 70%, ${60 - intensity * 20}%)`;
}

export function EmbeddingViewer({ vector, dimensions, isLoading, modelName }) {
  if (isLoading) return <SkeletonCard className="h-48" />;

  if (!vector || vector.length === 0) {
    return (
      <EmptyState
        icon={Sigma}
        title="No embedding available"
        description="Select a chunk to preview its embedding vector."
      />
    );
  }

  const preview = vector.slice(0, 512);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Embedding vector</CardTitle>
        <CardDescription>
          {modelName ? `${modelName} · ` : ''}
          {formatCompactNumber(dimensions || vector.length)} dimensions
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="embedding-heatmap">
          {preview.map((value, index) => (
            <div
              key={index}
              className="embedding-cell"
              style={{ backgroundColor: valueToColor(value) }}
              title={value.toFixed(4)}
            />
          ))}
        </div>
        {vector.length > preview.length ? (
          <p className="mt-2 text-2xs text-muted-foreground">
            Showing first {preview.length} of {formatCompactNumber(vector.length)} dimensions
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

// components/knowledge/MetadataViewer.jsx

import { Fragment } from 'react';
import { EmptyState } from '@/components/common/EmptyState';
import { FileJson } from 'lucide-react';
import '@/styles/knowledge.css';

function formatValue(value) {
  if (value === null || value === undefined) return '--';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function MetadataViewer({ metadata }) {
  const entries = metadata ? Object.entries(metadata) : [];

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={FileJson}
        title="No metadata"
        description="This item does not have any associated metadata."
      />
    );
  }

  return (
    <div className="metadata-grid">
      {entries.map(([key, value]) => (
        <Fragment key={key}>
          <span className="metadata-key">{key}</span>
          <span className="metadata-value">{formatValue(value)}</span>
        </Fragment>
      ))}
    </div>
  );
}

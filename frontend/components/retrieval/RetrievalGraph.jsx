// components/retrieval/RetrievalGraph.jsx

'use client';

import { useMemo } from 'react';
import { EmptyState } from '@/components/common/EmptyState';
import { Share2 } from 'lucide-react';
import { truncate } from '@/lib/utils';
import '@/styles/retrieval.css';

function layoutNodes(nodes, width, height) {
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 2 - 80;

  const rootNode = nodes.find((node) => node.is_root) || nodes[0];
  const otherNodes = nodes.filter((node) => node.id !== rootNode?.id);

  const positioned = new Map();
  if (rootNode) {
    positioned.set(rootNode.id, { x: centerX, y: centerY, node: rootNode });
  }

  otherNodes.forEach((node, index) => {
    const angle = (2 * Math.PI * index) / Math.max(otherNodes.length, 1);
    positioned.set(node.id, {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      node,
    });
  });

  return positioned;
}

export function RetrievalGraph({ nodes, edges, width = 640, height = 420 }) {
  const positions = useMemo(() => layoutNodes(nodes || [], width, height), [nodes, width, height]);

  if (!nodes || nodes.length === 0) {
    return (
      <EmptyState
        icon={Share2}
        title="No graph data"
        description="Run a GraphRAG query to visualize entity and chunk relationships."
      />
    );
  }

  return (
    <div className="card-surface overflow-hidden p-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full">
        {(edges || []).map((edge, index) => {
          const source = positions.get(edge.source);
          const target = positions.get(edge.target);
          if (!source || !target) return null;
          return (
            <line
              key={`${edge.source}-${edge.target}-${index}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              className="retrieval-graph-edge"
              data-active={edge.active ? 'true' : 'false'}
            />
          );
        })}

        {Array.from(positions.values()).map(({ x, y, node }) => (
          <g key={node.id} transform={`translate(${x}, ${y})`}>
            <circle
              r={node.is_root ? 26 : 20}
              fill={node.is_root ? 'hsl(var(--primary))' : 'hsl(var(--card))'}
              stroke="hsl(var(--border))"
              strokeWidth="1.5"
            />
            <text
              textAnchor="middle"
              dy="4"
              fontSize="9"
              fill={node.is_root ? 'hsl(var(--primary-foreground))' : 'hsl(var(--foreground))'}
            >
              {truncate(node.label, 10)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

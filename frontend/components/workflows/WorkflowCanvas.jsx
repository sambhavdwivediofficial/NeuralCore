// frontend/components/workflows/WorkflowCanvas.jsx

'use client';

import { useRef, useState } from 'react';
import { Play, Zap, GitBranch, Box, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const NODE_ICONS = {
  trigger: Zap,
  action: Play,
  condition: GitBranch,
  output: Box,
};

const DEFAULT_NODES = [
  { id: 'n1', type: 'trigger', label: 'Query Input', x: 60, y: 120, description: 'User query received' },
  { id: 'n2', type: 'action', label: 'Retrieval', x: 260, y: 80, description: 'Hybrid vector + BM25' },
  { id: 'n3', type: 'action', label: 'Reranking', x: 260, y: 180, description: 'BGE cross-encoder' },
  { id: 'n4', type: 'action', label: 'Prompt Build', x: 460, y: 120, description: 'Context compression' },
  { id: 'n5', type: 'output', label: 'LLM Response', x: 640, y: 120, description: 'Roxan 48B' },
];

const DEFAULT_EDGES = [
  { id: 'e1', from: 'n1', to: 'n2' },
  { id: 'e2', from: 'n1', to: 'n3' },
  { id: 'e3', from: 'n2', to: 'n4' },
  { id: 'e4', from: 'n3', to: 'n4' },
  { id: 'e5', from: 'n4', to: 'n5' },
];

function getNodeCenter(node) {
  return { x: node.x + 72, y: node.y + 32 };
}

function EdgePath({ from, to, nodes }) {
  const fromNode = nodes.find((n) => n.id === from);
  const toNode = nodes.find((n) => n.id === to);
  if (!fromNode || !toNode) return null;
  const f = getNodeCenter(fromNode);
  const t = getNodeCenter(toNode);
  const mx = (f.x + t.x) / 2;
  return (
    <path
      d={`M ${f.x} ${f.y} C ${mx} ${f.y}, ${mx} ${t.y}, ${t.x} ${t.y}`}
      className="workflow-edge"
    />
  );
}

export function WorkflowCanvas({ nodes = DEFAULT_NODES, edges = DEFAULT_EDGES, readOnly = false }) {
  const [selected, setSelected] = useState(null);
  const [nodeList, setNodeList] = useState(nodes);
  const dragRef = useRef(null);

  const handleMouseDown = (e, nodeId) => {
    if (readOnly) return;
    dragRef.current = {
      id: nodeId,
      startX: e.clientX,
      startY: e.clientY,
      origX: nodeList.find((n) => n.id === nodeId).x,
      origY: nodeList.find((n) => n.id === nodeId).y,
    };
    setSelected(nodeId);
    e.preventDefault();
  };

  const handleMouseMove = (e) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    setNodeList((prev) =>
      prev.map((n) =>
        n.id === dragRef.current.id
          ? { ...n, x: Math.max(0, dragRef.current.origX + dx), y: Math.max(0, dragRef.current.origY + dy) }
          : n
      )
    );
  };

  const handleMouseUp = () => { dragRef.current = null; };

  const selectedNode = nodeList.find((n) => n.id === selected);

  return (
    <div className="flex flex-col gap-3 h-full">
      <div
        className="workflow-canvas flex-1 select-none"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ minHeight: '20rem', cursor: dragRef.current ? 'grabbing' : 'default' }}
      >
        <div className="workflow-canvas-grid" />
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ zIndex: 1 }}
        >
          {edges.map((edge) => (
            <EdgePath key={edge.id} from={edge.from} to={edge.to} nodes={nodeList} />
          ))}
        </svg>

        {nodeList.map((node) => {
          const Icon = NODE_ICONS[node.type] ?? Box;
          return (
            <div
              key={node.id}
              className="workflow-node"
              data-type={node.type}
              style={{ left: node.x, top: node.y, zIndex: 2 }}
              onMouseDown={(e) => handleMouseDown(e, node.id)}
              onClick={() => setSelected(node.id === selected ? null : node.id)}
            >
              <div className="flex items-center gap-1.5">
                <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-semibold text-foreground">{node.label}</span>
              </div>
              {node.description && (
                <span className="text-muted-foreground text-[0.6875rem]">{node.description}</span>
              )}
              <div className="workflow-node-port" data-side="left" />
              <div className="workflow-node-port" data-side="right" />
            </div>
          );
        })}
      </div>

      {selectedNode && (
        <div className="rounded-lg border border-border bg-card p-3 flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary flex-shrink-0">
            {(() => { const I = NODE_ICONS[selectedNode.type] ?? Box; return <I className="h-3.5 w-3.5" />; })()}
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-semibold text-foreground">{selectedNode.label}</span>
            <span className="text-[0.6875rem] text-muted-foreground capitalize">{selectedNode.type} · {selectedNode.description}</span>
          </div>
          <button
            type="button"
            className="ml-auto text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setSelected(null)}
          >
            Deselect
          </button>
        </div>
      )}
    </div>
  );
}

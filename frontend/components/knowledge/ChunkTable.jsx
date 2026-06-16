// components/knowledge/ChunkTable.jsx

'use client';

import { Eye, FileSearch } from 'lucide-react';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/common/Table';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonTable } from '@/components/common/Loader';
import { truncate, formatCompactNumber } from '@/lib/utils';

export function ChunkTable({ chunks, isLoading, onView }) {
  if (isLoading) return <SkeletonTable rows={8} columns={5} />;

  if (!chunks || chunks.length === 0) {
    return (
      <EmptyState
        icon={FileSearch}
        title="No chunks found"
        description="Chunks will appear here once documents finish processing."
      />
    );
  }

  return (
    <div className="card-surface overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">Index</TableHead>
            <TableHead>Content preview</TableHead>
            <TableHead className="w-32">Document</TableHead>
            <TableHead className="w-24">Tokens</TableHead>
            <TableHead className="w-16" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {chunks.map((chunk) => (
            <TableRow key={chunk.id}>
              <TableCell className="text-xs text-muted-foreground">#{chunk.chunk_index}</TableCell>
              <TableCell className="max-w-md">
                <span className="text-sm text-foreground">{truncate(chunk.content, 140)}</span>
              </TableCell>
              <TableCell>
                <Badge variant="muted" className="max-w-[7rem] truncate">
                  {chunk.document_name}
                </Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {formatCompactNumber(chunk.token_count)}
              </TableCell>
              <TableCell>
                <Button variant="ghost" size="iconSm" onClick={() => onView?.(chunk)}>
                  <Eye className="h-3.5 w-3.5" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

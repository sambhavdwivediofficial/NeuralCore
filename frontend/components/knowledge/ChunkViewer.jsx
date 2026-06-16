// components/knowledge/ChunkViewer.jsx

'use client';

import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
} from '@/components/common/Modal';
import { Badge } from '@/components/common/Badge';
import { Separator } from '@/components/common/Separator';
import { formatCompactNumber } from '@/lib/utils';
import '@/styles/knowledge.css';

export function ChunkViewer({ chunk, open, onOpenChange }) {
  if (!chunk) return null;

  return (
    <Modal open={open} onOpenChange={onOpenChange}>
      <ModalContent className="max-w-2xl">
        <ModalHeader>
          <div className="flex items-center gap-2">
            <ModalTitle>Chunk #{chunk.chunk_index}</ModalTitle>
            <Badge variant="muted">{formatCompactNumber(chunk.token_count)} tokens</Badge>
          </div>
          <ModalDescription>From {chunk.document_name}</ModalDescription>
        </ModalHeader>

        <div className="scrollbar-thin max-h-72 overflow-y-auto rounded-md border border-border bg-muted/30 p-3">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
            {chunk.content}
          </p>
        </div>

        <Separator />

        <div className="metadata-grid">
          <span className="metadata-key">chunk_id</span>
          <span className="metadata-value">{chunk.id}</span>
          <span className="metadata-key">document_id</span>
          <span className="metadata-value">{chunk.document_id}</span>
          <span className="metadata-key">chunking_strategy</span>
          <span className="metadata-value">{chunk.chunking_strategy || '--'}</span>
          <span className="metadata-key">embedding_model</span>
          <span className="metadata-value">{chunk.embedding_model || '--'}</span>
          <span className="metadata-key">vector_dimension</span>
          <span className="metadata-value">{chunk.vector_dimension || '--'}</span>
        </div>
      </ModalContent>
    </Modal>
  );
}

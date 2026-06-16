// app/knowledge-bases/[kb_id]/chunks.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { SearchBar } from '@/components/common/SearchBar';
import { Pagination } from '@/components/common/Pagination';
import { ChunkTable } from '@/components/knowledge/ChunkTable';
import { ChunkViewer } from '@/components/knowledge/ChunkViewer';
import { useKnowledgeBase, useChunks } from '@/hooks/useKnowledgeBases';
import { ROUTES } from '@/lib/routes';
import { PAGINATION_DEFAULTS } from '@/lib/constants';

export default function KnowledgeBaseChunksPage({ params }) {
  const router = useRouter();
  const { knowledgeBase } = useKnowledgeBase(params.kb_id);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGINATION_DEFAULTS.PAGE_SIZE);
  const [selectedChunk, setSelectedChunk] = useState(null);

  const { chunks, total, isLoading } = useChunks(params.kb_id, {
    search,
    page,
    page_size: pageSize,
  });

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-2 w-fit"
            onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_DETAIL(params.kb_id))}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {knowledgeBase?.name}
          </Button>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Chunks</h1>
            <p className="text-sm text-muted-foreground">
              Browse every chunk indexed for this knowledge base
            </p>
          </div>
        </div>

        <SearchBar
          value={search}
          onChange={(value) => {
            setSearch(value);
            setPage(1);
          }}
          placeholder="Search chunk content"
          className="max-w-sm"
        />

        <ChunkTable chunks={chunks} isLoading={isLoading} onView={setSelectedChunk} />

        {!isLoading && total > 0 ? (
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
          />
        ) : null}
      </div>

      <ChunkViewer
        chunk={selectedChunk}
        open={Boolean(selectedChunk)}
        onOpenChange={(open) => !open && setSelectedChunk(null)}
      />
    </AppShell>
  );
}

// app/retrieval-debugger/chunks.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { SearchBar } from '@/components/common/SearchBar';
import { ChunkTable } from '@/components/knowledge/ChunkTable';
import { ChunkViewer } from '@/components/knowledge/ChunkViewer';
import { Pagination } from '@/components/common/Pagination';
import { useKnowledgeBases, useChunks } from '@/hooks/useKnowledgeBases';
import { useProjectContext } from '@/context/ProjectContext';
import { ROUTES } from '@/lib/routes';
import { PAGINATION_DEFAULTS } from '@/lib/constants';

export default function RetrievalChunksPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const { knowledgeBases } = useKnowledgeBases({ project_id: activeProjectId });
  const [kbId, setKbId] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGINATION_DEFAULTS.PAGE_SIZE);
  const [selectedChunk, setSelectedChunk] = useState(null);

  const { chunks, total, isLoading } = useChunks(kbId, { search, page, page_size: pageSize });

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.RETRIEVAL_DEBUGGER)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Retrieval debugger
        </Button>

        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Chunk inspector</h1>
          <p className="text-sm text-muted-foreground">
            Browse chunks across any knowledge base in this project
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Select value={kbId} onValueChange={setKbId}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Select knowledge base" />
            </SelectTrigger>
            <SelectContent>
              {knowledgeBases.map((kb) => (
                <SelectItem key={kb.id} value={kb.id}>
                  {kb.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <SearchBar
            value={search}
            onChange={(value) => {
              setSearch(value);
              setPage(1);
            }}
            placeholder="Search chunk content"
            className="max-w-sm"
          />
        </div>

        {!kbId ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            Select a knowledge base to inspect its chunks
          </p>
        ) : (
          <>
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
          </>
        )}
      </div>

      <ChunkViewer
        chunk={selectedChunk}
        open={Boolean(selectedChunk)}
        onOpenChange={(open) => !open && setSelectedChunk(null)}
      />
    </AppShell>
  );
}

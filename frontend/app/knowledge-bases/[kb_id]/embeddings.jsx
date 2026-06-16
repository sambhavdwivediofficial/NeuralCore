// app/knowledge-bases/[kb_id]/embeddings.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Layers } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { SearchBar } from '@/components/common/SearchBar';
import { EmptyState } from '@/components/common/EmptyState';
import { EmbeddingViewer } from '@/components/knowledge/EmbeddingViewer';
import { MetadataViewer } from '@/components/knowledge/MetadataViewer';
import { useKnowledgeBase, useChunks } from '@/hooks/useKnowledgeBases';
import { useEmbeddingCacheStats } from '@/hooks/useEmbeddings';
import { ROUTES } from '@/lib/routes';
import { truncate, formatCompactNumber } from '@/lib/utils';

export default function KnowledgeBaseEmbeddingsPage({ params }) {
  const router = useRouter();
  const { knowledgeBase } = useKnowledgeBase(params.kb_id);
  const [search, setSearch] = useState('');
  const { chunks, isLoading } = useChunks(params.kb_id, { search, page_size: 30 });
  const [selectedChunk, setSelectedChunk] = useState(null);
  const { stats: cacheStats } = useEmbeddingCacheStats();

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
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Embeddings</h1>
            <p className="text-sm text-muted-foreground">
              Inspect vector embeddings generated for chunks in this knowledge base
            </p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[18rem_1fr]">
          <Card>
            <CardHeader>
              <CardTitle>Chunks</CardTitle>
              <CardDescription>Select a chunk to inspect its embedding</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <SearchBar value={search} onChange={setSearch} placeholder="Search chunks" />
              <div className="scrollbar-thin flex max-h-96 flex-col gap-1 overflow-y-auto">
                {isLoading ? (
                  Array.from({ length: 6 }).map((_, index) => (
                    <div key={index} className="skeleton h-10 w-full rounded-md" />
                  ))
                ) : chunks.length === 0 ? (
                  <p className="py-6 text-center text-xs text-muted-foreground">No chunks found</p>
                ) : (
                  chunks.map((chunk) => (
                    <button
                      key={chunk.id}
                      onClick={() => setSelectedChunk(chunk)}
                      className={`interactive-row rounded-md px-2 py-2 text-left text-xs ${
                        selectedChunk?.id === chunk.id ? 'bg-accent' : ''
                      }`}
                    >
                      {truncate(chunk.content, 70)}
                    </button>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          <div className="flex flex-col gap-4">
            {!selectedChunk ? (
              <EmptyState
                icon={Layers}
                title="Select a chunk"
                description="Choose a chunk from the list to view its embedding vector and metadata."
              />
            ) : (
              <>
                <EmbeddingViewer
                  vector={selectedChunk.embedding_preview}
                  dimensions={selectedChunk.vector_dimension}
                  modelName={selectedChunk.embedding_model}
                />
                <Card>
                  <CardHeader>
                    <CardTitle>Chunk metadata</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <MetadataViewer metadata={selectedChunk.metadata} />
                  </CardContent>
                </Card>
              </>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Embedding cache</CardTitle>
                <CardDescription>Reduces redundant calls to the embedding provider</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-3">
                <div className="metric-tile">
                  <span className="metric-tile-label">Hits</span>
                  <span className="metric-tile-value">{formatCompactNumber(cacheStats?.hits)}</span>
                </div>
                <div className="metric-tile">
                  <span className="metric-tile-label">Misses</span>
                  <span className="metric-tile-value">{formatCompactNumber(cacheStats?.misses)}</span>
                </div>
                <div className="metric-tile">
                  <span className="metric-tile-label">Hit rate</span>
                  <span className="metric-tile-value">
                    {cacheStats?.hit_rate ? `${(cacheStats.hit_rate * 100).toFixed(1)}%` : '--'}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

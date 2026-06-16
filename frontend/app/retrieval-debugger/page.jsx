// app/retrieval-debugger/page.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Boxes, BarChart3, ListOrdered, ChevronRight } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { QueryBox } from '@/components/retrieval/QueryBox';
import { SearchResults } from '@/components/retrieval/SearchResults';
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { useProjectContext } from '@/context/ProjectContext';
import { useRetrievalQuery } from '@/hooks/useRetrieval';
import { RETRIEVAL_STRATEGIES } from '@/lib/constants';
import { ROUTES } from '@/lib/routes';
import { formatMs } from '@/lib/utils';
import { toast } from '@/components/common/Toast';
import '@/styles/retrieval.css';

const PIPELINE_STEPS = [
  'Query rewrite',
  'Vector search',
  'BM25 search',
  'Fusion',
  'Reranking',
  'Context build',
];

export default function RetrievalDebuggerPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const { knowledgeBases } = useKnowledgeBases({ project_id: activeProjectId });
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState(RETRIEVAL_STRATEGIES.HYBRID);
  const [topK, setTopK] = useState(10);
  const [knowledgeBaseId, setKnowledgeBaseId] = useState('');
  const { result, isLoading, runQuery } = useRetrievalQuery();

  const handleSubmit = async () => {
    try {
      await runQuery({ knowledge_base_id: knowledgeBaseId, query, strategy, top_k: topK });
    } catch (error) {
      toast.error('Retrieval query failed');
    }
  };

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Retrieval debugger</h1>
          <p className="text-sm text-muted-foreground">
            Test queries end-to-end and inspect every stage of the retrieval pipeline
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <button
            onClick={() => router.push(`${ROUTES.RETRIEVAL_DEBUGGER}/chunks`)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <Boxes className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Chunk inspector</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => router.push(`${ROUTES.RETRIEVAL_DEBUGGER}/metrics`)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Metrics</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => router.push(`${ROUTES.RETRIEVAL_DEBUGGER}/reranking`)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <ListOrdered className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Reranking</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Run a query</CardTitle>
            <CardDescription>Test retrieval against any knowledge base in this project</CardDescription>
          </CardHeader>
          <CardContent>
            <QueryBox
              query={query}
              onQueryChange={setQuery}
              strategy={strategy}
              onStrategyChange={setStrategy}
              topK={topK}
              onTopKChange={setTopK}
              knowledgeBaseId={knowledgeBaseId}
              onKnowledgeBaseChange={setKnowledgeBaseId}
              knowledgeBases={knowledgeBases}
              onSubmit={handleSubmit}
              isLoading={isLoading}
            />
          </CardContent>
        </Card>

        {result ? (
          <Card>
            <CardHeader>
              <CardTitle>Pipeline trace</CardTitle>
              <CardDescription>Completed in {formatMs(result.latency_ms)}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap items-center gap-2">
                {PIPELINE_STEPS.map((step, index) => (
                  <div key={step} className="flex items-center gap-2">
                    <span className="query-pipeline-step">{step}</span>
                    {index < PIPELINE_STEPS.length - 1 ? (
                      <span className="query-pipeline-connector">
                        <ChevronRight className="h-3.5 w-3.5" />
                      </span>
                    ) : null}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent>
            <SearchResults results={result?.results} isLoading={isLoading} />
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

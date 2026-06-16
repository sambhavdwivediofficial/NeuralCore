// app/knowledge-bases/[kb_id]/retrieval.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Search } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Textarea } from '@/components/common/Textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { EmptyState } from '@/components/common/EmptyState';
import { useKnowledgeBase } from '@/hooks/useKnowledgeBases';
import { useRetrievalQuery } from '@/hooks/useRetrieval';
import { ROUTES } from '@/lib/routes';
import { RETRIEVAL_STRATEGIES, RETRIEVAL_STRATEGY_LABELS } from '@/lib/constants';
import { classNamesByScore, formatMs } from '@/lib/utils';
import { toast } from '@/components/common/Toast';
import '@/styles/retrieval.css';

export default function KnowledgeBaseRetrievalPage({ params }) {
  const router = useRouter();
  const { knowledgeBase } = useKnowledgeBase(params.kb_id);
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState(RETRIEVAL_STRATEGIES.HYBRID);
  const { result, isLoading, runQuery } = useRetrievalQuery();

  const handleSearch = async () => {
    if (!query.trim()) return;
    try {
      await runQuery({
        knowledge_base_id: params.kb_id,
        query,
        strategy,
        top_k: 10,
      });
    } catch (error) {
      toast.error('Retrieval query failed');
    }
  };

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
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Test retrieval</h1>
            <p className="text-sm text-muted-foreground">
              Run a query against this knowledge base and inspect the retrieved chunks
            </p>
          </div>
        </div>

        <Card>
          <CardContent className="flex flex-col gap-3 p-4">
            <Textarea
              rows={3}
              placeholder="Ask a question about this knowledge base..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="flex items-center justify-between gap-3">
              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger className="w-56">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(RETRIEVAL_STRATEGIES).map((value) => (
                    <SelectItem key={value} value={value}>
                      {RETRIEVAL_STRATEGY_LABELS[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={handleSearch} isLoading={isLoading} disabled={!query.trim()}>
                <Search className="h-3.5 w-3.5" />
                Run query
              </Button>
            </div>
          </CardContent>
        </Card>

        {!result ? (
          <EmptyState
            icon={Search}
            title="No query run yet"
            description="Enter a query above to see retrieved chunks ranked by relevance score."
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Results</CardTitle>
              <CardDescription>
                {result.results?.length || 0} chunks retrieved in {formatMs(result.latency_ms)}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {result.results?.map((item, index) => (
                <div key={item.chunk_id} className="retrieval-result-card">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="retrieval-result-rank" data-rank={String(index + 1)}>
                        {index + 1}
                      </span>
                      <span className="text-xs text-muted-foreground">{item.document_name}</span>
                    </div>
                    <span className="text-xs font-medium text-foreground">
                      {item.score.toFixed(4)}
                    </span>
                  </div>
                  <p className="text-sm text-foreground">{item.content}</p>
                  <div className="score-bar-track">
                    <div
                      className="score-bar-fill"
                      data-tier={classNamesByScore(item.score)}
                      style={{ width: `${Math.min(100, item.score * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

// app/retrieval-debugger/reranking.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ListOrdered } from 'lucide-react';
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
import { RerankViewer } from '@/components/retrieval/RerankViewer';
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { useProjectContext } from '@/context/ProjectContext';
import { compareRerankStrategies } from '@/services/reranking';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { RERANK_STRATEGIES } from '@/lib/constants';

const RERANK_LABELS = {
  [RERANK_STRATEGIES.RRF]: 'Reciprocal Rank Fusion',
  [RERANK_STRATEGIES.WEIGHTED]: 'Weighted fusion',
  [RERANK_STRATEGIES.BORDA]: 'Borda count',
  [RERANK_STRATEGIES.SOFTMAX]: 'Softmax fusion',
  [RERANK_STRATEGIES.SCORE_NORMALIZATION]: 'Score normalization',
  [RERANK_STRATEGIES.LINEAR]: 'Linear combination',
};

export default function RetrievalRerankingPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const { knowledgeBases } = useKnowledgeBases({ project_id: activeProjectId });
  const [kbId, setKbId] = useState('');
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState(RERANK_STRATEGIES.RRF);
  const [comparison, setComparison] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCompare = async () => {
    if (!query.trim() || !kbId) return;
    setIsLoading(true);
    try {
      const result = await compareRerankStrategies({
        knowledge_base_id: kbId,
        query,
        rerank_strategy: strategy,
      });
      setComparison(result);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

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
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Reranking comparison</h1>
          <p className="text-sm text-muted-foreground">
            Compare result ordering before and after applying a reranking strategy
          </p>
        </div>

        <Card>
          <CardContent className="flex flex-col gap-4 p-4">
            <Textarea
              rows={3}
              placeholder="Enter a query..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Select value={kbId} onValueChange={setKbId}>
                <SelectTrigger>
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

              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(RERANK_STRATEGIES).map((value) => (
                    <SelectItem key={value} value={value}>
                      {RERANK_LABELS[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end">
              <Button onClick={handleCompare} isLoading={isLoading} disabled={!query.trim() || !kbId}>
                <ListOrdered className="h-3.5 w-3.5" />
                Compare ranking
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Before vs after reranking</CardTitle>
            <CardDescription>
              Left position shows initial retrieval order, right shows order after{' '}
              {RERANK_LABELS[strategy]}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RerankViewer beforeResults={comparison?.before} afterResults={comparison?.after} />
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

// app/retrieval-debugger/query.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Wand2 } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Textarea } from '@/components/common/Textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { Checkbox } from '@/components/common/Checkbox';
import { Label } from '@/components/common/Label';
import { EmptyState } from '@/components/common/EmptyState';
import { getQueryRewrites } from '@/services/retrieval';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';

const STRATEGIES = [
  { id: 'hyde', label: 'HyDE (Hypothetical Document Embeddings)' },
  { id: 'step_back', label: 'Step-back prompting' },
  { id: 'decomposition', label: 'Query decomposition' },
  { id: 'expansion', label: 'Query expansion' },
  { id: 'splade', label: 'SPLADE sparse expansion' },
];

export default function RetrievalQueryPage() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(['hyde', 'decomposition']);
  const [rewrites, setRewrites] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const toggleStrategy = (id) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  };

  const handleRun = async () => {
    if (!query.trim()) return;
    setIsLoading(true);
    try {
      const result = await getQueryRewrites({ query, strategies: selected });
      setRewrites(result);
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
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Query rewriting</h1>
          <p className="text-sm text-muted-foreground">
            Preview how each query rewriting strategy transforms a raw user query
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

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {STRATEGIES.map((strategy) => (
                <label key={strategy.id} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={selected.includes(strategy.id)}
                    onCheckedChange={() => toggleStrategy(strategy.id)}
                  />
                  <Label className="cursor-pointer font-normal">{strategy.label}</Label>
                </label>
              ))}
            </div>

            <div className="flex justify-end">
              <Button onClick={handleRun} isLoading={isLoading} disabled={!query.trim()}>
                <Wand2 className="h-3.5 w-3.5" />
                Generate rewrites
              </Button>
            </div>
          </CardContent>
        </Card>

        {!rewrites ? (
          <EmptyState
            icon={Wand2}
            title="No rewrites generated yet"
            description="Enter a query and select strategies to see how it gets transformed."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {Object.entries(rewrites).map(([strategyId, value]) => (
              <Card key={strategyId}>
                <CardHeader>
                  <CardTitle className="capitalize">{strategyId.replace('_', ' ')}</CardTitle>
                  <CardDescription>Transformed query representation</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap rounded-md bg-muted/40 p-3 font-mono text-xs text-foreground">
                    {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

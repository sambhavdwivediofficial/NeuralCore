// components/retrieval/QueryBox.jsx

'use client';

import { Search } from 'lucide-react';
import { Textarea } from '@/components/common/Textarea';
import { Button } from '@/components/common/Button';
import { Label } from '@/components/common/Label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { RETRIEVAL_STRATEGIES, RETRIEVAL_STRATEGY_LABELS } from '@/lib/constants';

export function QueryBox({
  query,
  onQueryChange,
  strategy,
  onStrategyChange,
  topK,
  onTopKChange,
  knowledgeBaseId,
  onKnowledgeBaseChange,
  knowledgeBases = [],
  onSubmit,
  isLoading,
}) {
  return (
    <div className="flex flex-col gap-3">
      <Textarea
        rows={3}
        placeholder="Enter a query to test retrieval..."
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <Label className="text-2xs">Knowledge base</Label>
          <Select value={knowledgeBaseId} onValueChange={onKnowledgeBaseChange}>
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
        </div>

        <div className="flex flex-col gap-1.5">
          <Label className="text-2xs">Strategy</Label>
          <Select value={strategy} onValueChange={onStrategyChange}>
            <SelectTrigger>
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
        </div>

        <div className="flex flex-col gap-1.5">
          <Label className="text-2xs">Top K</Label>
          <Select value={String(topK)} onValueChange={(value) => onTopKChange(Number(value))}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[5, 10, 20, 50].map((value) => (
                <SelectItem key={value} value={String(value)}>
                  {value} results
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={onSubmit} isLoading={isLoading} disabled={!query.trim() || !knowledgeBaseId}>
          <Search className="h-3.5 w-3.5" />
          Run query
        </Button>
      </div>
    </div>
  );
}

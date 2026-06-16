// app/knowledge-bases/create.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Database } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Textarea } from '@/components/common/Textarea';
import { Label } from '@/components/common/Label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { knowledgeBaseSchema } from '@/lib/validators';
import { createKnowledgeBase } from '@/services/knowledgebases';
import { useProjectContext } from '@/context/ProjectContext';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import {
  VECTOR_STORE_PROVIDERS,
  VECTOR_STORE_LABELS,
  EMBEDDING_PROVIDERS,
  CHUNKING_STRATEGIES,
} from '@/lib/constants';

const EMBEDDING_LABELS = {
  [EMBEDDING_PROVIDERS.OPENAI]: 'OpenAI',
  [EMBEDDING_PROVIDERS.BGE]: 'BGE',
  [EMBEDDING_PROVIDERS.E5]: 'E5',
  [EMBEDDING_PROVIDERS.JINA]: 'Jina',
  [EMBEDDING_PROVIDERS.NOMIC]: 'Nomic',
  [EMBEDDING_PROVIDERS.SENTENCE_TRANSFORMERS]: 'Sentence Transformers',
  [EMBEDDING_PROVIDERS.CUSTOM]: 'Custom HTTP',
};

const CHUNKING_LABELS = {
  [CHUNKING_STRATEGIES.FIXED_SIZE]: 'Fixed size',
  [CHUNKING_STRATEGIES.RECURSIVE]: 'Recursive',
  [CHUNKING_STRATEGIES.SEMANTIC]: 'Semantic',
  [CHUNKING_STRATEGIES.SENTENCE]: 'Sentence',
  [CHUNKING_STRATEGIES.MARKDOWN]: 'Markdown-aware',
  [CHUNKING_STRATEGIES.CODE]: 'Code-aware',
  [CHUNKING_STRATEGIES.TOKEN]: 'Token-based',
  [CHUNKING_STRATEGIES.HIERARCHICAL]: 'Hierarchical',
};

export default function CreateKnowledgeBasePage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(knowledgeBaseSchema),
    defaultValues: {
      name: '',
      description: '',
      vectorStore: VECTOR_STORE_PROVIDERS.QDRANT,
      embeddingProvider: EMBEDDING_PROVIDERS.OPENAI,
      chunkingStrategy: CHUNKING_STRATEGIES.RECURSIVE,
      chunkSize: 512,
      chunkOverlap: 50,
    },
  });

  const onSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      const kb = await createKnowledgeBase({
        project_id: activeProjectId,
        name: values.name,
        description: values.description,
        vector_store: values.vectorStore,
        embedding_provider: values.embeddingProvider,
        chunking_strategy: values.chunkingStrategy,
        chunk_size: values.chunkSize,
        chunk_overlap: values.chunkOverlap,
      });
      toast.success('Knowledge base created');
      router.push(ROUTES.KNOWLEDGE_BASE_DETAIL(kb.id));
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => router.back()}>
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </Button>

        <Card>
          <CardHeader>
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Database className="h-4 w-4" />
            </div>
            <CardTitle className="mt-2">Create a knowledge base</CardTitle>
            <CardDescription>
              Configure how documents will be chunked, embedded, and stored for retrieval.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="Product documentation" {...register('name')} />
                {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" rows={2} {...register('description')} />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label>Vector store</Label>
                  <Select
                    value={watch('vectorStore')}
                    onValueChange={(value) => setValue('vectorStore', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.values(VECTOR_STORE_PROVIDERS).map((provider) => (
                        <SelectItem key={provider} value={provider}>
                          {VECTOR_STORE_LABELS[provider]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label>Embedding provider</Label>
                  <Select
                    value={watch('embeddingProvider')}
                    onValueChange={(value) => setValue('embeddingProvider', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.values(EMBEDDING_PROVIDERS).map((provider) => (
                        <SelectItem key={provider} value={provider}>
                          {EMBEDDING_LABELS[provider]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Chunking strategy</Label>
                <Select
                  value={watch('chunkingStrategy')}
                  onValueChange={(value) => setValue('chunkingStrategy', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.values(CHUNKING_STRATEGIES).map((strategy) => (
                      <SelectItem key={strategy} value={strategy}>
                        {CHUNKING_LABELS[strategy]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="chunkSize">Chunk size (tokens)</Label>
                  <Input
                    id="chunkSize"
                    type="number"
                    {...register('chunkSize', { valueAsNumber: true })}
                  />
                  {errors.chunkSize ? (
                    <p className="text-xs text-destructive">{errors.chunkSize.message}</p>
                  ) : null}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="chunkOverlap">Chunk overlap (tokens)</Label>
                  <Input
                    id="chunkOverlap"
                    type="number"
                    {...register('chunkOverlap', { valueAsNumber: true })}
                  />
                  {errors.chunkOverlap ? (
                    <p className="text-xs text-destructive">{errors.chunkOverlap.message}</p>
                  ) : null}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => router.back()}>
                  Cancel
                </Button>
                <Button type="submit" isLoading={isSubmitting}>
                  Create knowledge base
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

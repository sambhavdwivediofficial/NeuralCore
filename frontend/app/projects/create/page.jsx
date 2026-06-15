// app/projects/create/page.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, FolderPlus } from 'lucide-react';
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
import { projectSchema } from '@/lib/validators';
import { createProject } from '@/services/projects';
import { useProjectContext } from '@/context/ProjectContext';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { LLM_PROVIDERS, LLM_PROVIDER_LABELS, EMBEDDING_PROVIDERS } from '@/lib/constants';

const EMBEDDING_LABELS = {
  [EMBEDDING_PROVIDERS.OPENAI]: 'OpenAI',
  [EMBEDDING_PROVIDERS.BGE]: 'BGE',
  [EMBEDDING_PROVIDERS.E5]: 'E5',
  [EMBEDDING_PROVIDERS.JINA]: 'Jina',
  [EMBEDDING_PROVIDERS.NOMIC]: 'Nomic',
  [EMBEDDING_PROVIDERS.SENTENCE_TRANSFORMERS]: 'Sentence Transformers',
  [EMBEDDING_PROVIDERS.CUSTOM]: 'Custom HTTP',
};

export default function CreateProjectPage() {
  const router = useRouter();
  const { refresh, setActiveProject } = useProjectContext();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      name: '',
      description: '',
      defaultLlmProvider: LLM_PROVIDERS.OPENAI,
      defaultEmbeddingProvider: EMBEDDING_PROVIDERS.OPENAI,
    },
  });

  const onSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      const project = await createProject({
        name: values.name,
        description: values.description,
        default_llm_provider: values.defaultLlmProvider,
        default_embedding_provider: values.defaultEmbeddingProvider,
      });
      toast.success('Project created');
      await refresh();
      setActiveProject(project.id);
      router.push(ROUTES.PROJECT_DETAIL(project.id));
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
              <FolderPlus className="h-4 w-4" />
            </div>
            <CardTitle className="mt-2">Create a new project</CardTitle>
            <CardDescription>
              Projects group knowledge bases, agents, and configuration under a single workspace.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="name">Project name</Label>
                <Input id="name" placeholder="Customer Support Assistant" {...register('name')} />
                {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="What is this project for?"
                  rows={3}
                  {...register('description')}
                />
                {errors.description ? (
                  <p className="text-xs text-destructive">{errors.description.message}</p>
                ) : null}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label>Default LLM provider</Label>
                  <Select
                    value={watch('defaultLlmProvider')}
                    onValueChange={(value) => setValue('defaultLlmProvider', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.values(LLM_PROVIDERS).map((provider) => (
                        <SelectItem key={provider} value={provider}>
                          {LLM_PROVIDER_LABELS[provider]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.defaultLlmProvider ? (
                    <p className="text-xs text-destructive">{errors.defaultLlmProvider.message}</p>
                  ) : null}
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label>Default embedding provider</Label>
                  <Select
                    value={watch('defaultEmbeddingProvider')}
                    onValueChange={(value) => setValue('defaultEmbeddingProvider', value)}
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
                  {errors.defaultEmbeddingProvider ? (
                    <p className="text-xs text-destructive">{errors.defaultEmbeddingProvider.message}</p>
                  ) : null}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => router.back()}>
                  Cancel
                </Button>
                <Button type="submit" isLoading={isSubmitting}>
                  Create project
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

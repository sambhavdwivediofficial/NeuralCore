// app/projects/[project_id]/settings.jsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Trash2 } from 'lucide-react';
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
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from '@/components/common/Card';
import { Separator } from '@/components/common/Separator';
import { PageLoader } from '@/components/common/Loader';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from '@/components/common/Modal';
import { projectSchema } from '@/lib/validators';
import { useProject } from '@/hooks/useProjects';
import { updateProject, deleteProject } from '@/services/projects';
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

export default function ProjectSettingsPage({ params }) {
  const router = useRouter();
  const { project, isLoading, refresh } = useProject(params.project_id);
  const { refresh: refreshProjectList } = useProjectContext();
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
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

  useEffect(() => {
    if (project) {
      reset({
        name: project.name,
        description: project.description || '',
        defaultLlmProvider: project.default_llm_provider,
        defaultEmbeddingProvider: project.default_embedding_provider,
      });
    }
  }, [project, reset]);

  const onSubmit = async (values) => {
    setIsSaving(true);
    try {
      await updateProject(params.project_id, {
        name: values.name,
        description: values.description,
        default_llm_provider: values.defaultLlmProvider,
        default_embedding_provider: values.defaultEmbeddingProvider,
      });
      toast.success('Project settings saved');
      refresh();
      refreshProjectList();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteProject(params.project_id);
      toast.success('Project deleted');
      refreshProjectList();
      router.push(ROUTES.PROJECTS);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <AppShell>
        <PageLoader label="Loading settings" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.PROJECT_DETAIL(params.project_id))}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {project?.name}
        </Button>

        <Card>
          <CardHeader>
            <CardTitle>General settings</CardTitle>
            <CardDescription>Update project name, description, and default providers</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="name">Project name</Label>
                <Input id="name" {...register('name')} />
                {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" rows={3} {...register('description')} />
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
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button type="submit" isLoading={isSaving}>
                  Save changes
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle className="text-destructive">Danger zone</CardTitle>
            <CardDescription>
              Deleting this project removes all knowledge bases, agents, and configuration
              permanently.
            </CardDescription>
          </CardHeader>
          <Separator />
          <CardFooter className="justify-end pt-4">
            <Button variant="destructive" onClick={() => setShowDeleteModal(true)}>
              <Trash2 className="h-3.5 w-3.5" />
              Delete project
            </Button>
          </CardFooter>
        </Card>
      </div>

      <Modal open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Delete project</ModalTitle>
            <ModalDescription>
              This will permanently delete &quot;{project?.name}&quot; and all associated data. This
              action cannot be undone.
            </ModalDescription>
          </ModalHeader>
          <ModalFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isDeleting} onClick={handleDelete}>
              Delete project
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}

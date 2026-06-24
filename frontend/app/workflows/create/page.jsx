// frontend/app/workflows/create/page.jsx

'use client';

import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { Textarea } from '@/components/common/Textarea';
import { Select } from '@/components/common/Select';
import { workflowSchema } from '@/lib/validators';
import { useWorkflows } from '@/hooks/useWorkflows';
import { useProjects } from '@/hooks/useProjects';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

const TEMPLATES = [
  { value: 'rag', label: 'RAG — Retrieval + Answer' },
  { value: 'agentic_rag', label: 'Agentic RAG — Agent + Retrieval' },
  { value: 'research', label: 'Research — Deep multi-step research' },
  { value: 'code_assistant', label: 'Code Assistant — Coding + Explanation' },
  { value: '', label: 'Custom — Build from scratch' },
];

export default function WorkflowCreatePage() {
  const router = useRouter();
  const { create } = useWorkflows();
  const { projects } = useProjects();

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(workflowSchema),
    defaultValues: { name: '', project_id: '', description: '', template: 'rag' },
  });

  const onSubmit = async (values) => {
    try {
      const wf = await create({ ...values, template: values.template || undefined });
      router.push(ROUTES.WORKFLOW(wf.id));
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href={ROUTES.WORKFLOWS}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold text-foreground">New workflow</h1>
          <p className="text-xs text-muted-foreground">Configure a pipeline template</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card-surface p-6 flex flex-col gap-5">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name">Workflow name</Label>
          <Input id="name" placeholder="e.g. Finance RAG Pipeline" {...register('name')} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="project_id">Project</Label>
          <Select id="project_id" {...register('project_id')}>
            <option value="">Select a project</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
          {errors.project_id && <p className="text-xs text-destructive">{errors.project_id.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="template">Template</Label>
          <Select id="template" {...register('template')}>
            {TEMPLATES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="description">Description <span className="text-muted-foreground">(optional)</span></Label>
          <Textarea id="description" rows={3} placeholder="What does this workflow do?" {...register('description')} />
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="submit" isLoading={isSubmitting}>Create workflow</Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
        </div>
      </form>
    </div>
  );
}

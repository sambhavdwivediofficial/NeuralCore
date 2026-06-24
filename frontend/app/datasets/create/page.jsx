// frontend/app/datasets/create/page.jsx

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
import { datasetSchema } from '@/lib/validators';
import { useDatasets } from '@/hooks/useDatasets';
import { useProjects } from '@/hooks/useProjects';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

const FORMATS = [
  { value: 'alpaca', label: 'Alpaca — instruction/input/output' },
  { value: 'sharegpt', label: 'ShareGPT — conversations array' },
  { value: 'openai', label: 'OpenAI — messages format' },
  { value: 'custom', label: 'Custom — define your own schema' },
];

export default function DatasetCreatePage() {
  const router = useRouter();
  const { create } = useDatasets();
  const { projects } = useProjects();

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(datasetSchema),
    defaultValues: { name: '', project_id: '', format: 'alpaca', description: '' },
  });

  const onSubmit = async (values) => {
    try {
      await create(values);
      toast.success('Dataset created');
      router.push(ROUTES.DATASETS);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href={ROUTES.DATASETS}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold text-foreground">New dataset</h1>
          <p className="text-xs text-muted-foreground">Create a fine-tuning dataset</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card-surface p-6 flex flex-col gap-5">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name">Dataset name</Label>
          <Input id="name" placeholder="e.g. Finance QA Dataset" {...register('name')} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="project_id">Project</Label>
            <Select id="project_id" {...register('project_id')}>
              <option value="">Select a project</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
            {errors.project_id && <p className="text-xs text-destructive">{errors.project_id.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="format">Format</Label>
            <Select id="format" {...register('format')}>
              {FORMATS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
            </Select>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="description">Description <span className="text-muted-foreground">(optional)</span></Label>
          <Textarea id="description" rows={3} placeholder="What is this dataset for?" {...register('description')} />
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="submit" isLoading={isSubmitting}>Create dataset</Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
        </div>
      </form>
    </div>
  );
}

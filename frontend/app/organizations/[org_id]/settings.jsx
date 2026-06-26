// frontend/app/organizations/[org_id]/settings.jsx

'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { PageLoader as Loader } from '@/components/common/Loader';
import { organizationSchema } from '@/lib/validators';
import { useOrganization } from '@/hooks/useOrganizations';
import { useOrganizationContext } from '@/context/OrganizationContext';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

export default function OrganizationSettingsPage() {
  const { org_id } = useParams();
  const router = useRouter();
  const { organization, isLoading, update } = useOrganization(org_id);
  const { updateActiveOrg } = useOrganizationContext();

  const { register, handleSubmit, reset, formState: { errors, isSubmitting, isDirty } } = useForm({
    resolver: zodResolver(organizationSchema),
    defaultValues: { name: '', billing_email: '' },
  });

  useEffect(() => {
    if (organization) {
      reset({ name: organization.name, billing_email: organization.billing_email ?? '' });
    }
  }, [organization, reset]);

  const onSubmit = async (values) => {
    try {
      const updated = await update({ name: values.name, billing_email: values.billing_email || null });
      updateActiveOrg(updated);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (!organization) return <div className="p-6 text-sm text-muted-foreground">Organization not found.</div>;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Link href={ROUTES.ORGANIZATION(org_id)}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold text-foreground">Organization settings</h1>
          <p className="text-xs text-muted-foreground">{organization.name}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card-surface p-6 flex flex-col gap-5">
        <h2 className="text-sm font-semibold text-foreground">General</h2>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name">Organization name</Label>
          <Input id="name" {...register('name')} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="billing_email">Billing email</Label>
          <Input id="billing_email" type="email" placeholder="billing@company.com" {...register('billing_email')} />
          {errors.billing_email && <p className="text-xs text-destructive">{errors.billing_email.message}</p>}
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="submit" isLoading={isSubmitting} disabled={!isDirty}>Save changes</Button>
          <Button type="button" variant="outline" onClick={() => reset()}>Reset</Button>
        </div>
      </form>

      <div className="card-surface p-6 flex flex-col gap-4 border-destructive/30">
        <div className="flex flex-col gap-1">
          <h2 className="text-sm font-semibold text-destructive">Danger zone</h2>
          <p className="text-xs text-muted-foreground">These actions are irreversible. Proceed with caution.</p>
        </div>
        <div className="flex items-center justify-between gap-4 rounded-md border border-destructive/20 p-4">
          <div className="flex flex-col gap-0.5">
            <p className="text-xs font-medium text-foreground">Delete organization</p>
            <p className="text-xs text-muted-foreground">Permanently deletes all projects, agents, knowledge bases, and data.</p>
          </div>
          <button type="button"
            onClick={() => toast.error('Contact support to delete an organization.')}
            className="flex items-center gap-1.5 rounded-md border border-destructive/30 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/5 transition-colors flex-shrink-0">
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </button>
        </div>
      </div>
    </div>
  );
}

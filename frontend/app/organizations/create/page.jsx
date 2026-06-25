// frontend/app/organizations/create/page.jsx

'use client';

import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Building2 } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { organizationSchema } from '@/lib/validators';
import { useOrganizationContext } from '@/context/OrganizationContext';
import * as orgService from '@/services/organizations';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

export default function OrganizationCreatePage() {
  const router = useRouter();
  const { addOrg } = useOrganizationContext();

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(organizationSchema),
    defaultValues: { name: '', billing_email: '' },
  });

  const onSubmit = async (values) => {
    try {
      const payload = { name: values.name };
      if (values.billing_email) payload.billing_email = values.billing_email;
      const org = await orgService.createOrganization(payload);
      addOrg(org);
      toast.success('Organization created — 14-day trial started');
      router.push(ROUTES.ORGANIZATION(org.id));
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-lg">
      <div className="flex items-center gap-3">
        <Link href={ROUTES.ORGANIZATIONS}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold text-foreground">New organization</h1>
          <p className="text-xs text-muted-foreground">14-day free trial · no credit card required</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card-surface p-6 flex flex-col gap-5">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name">Organization name</Label>
          <div className="relative">
            <Input id="name" placeholder="Acme Inc." className="pl-9" {...register('name')} />
            <Building2 className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          </div>
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="billing_email">Billing email <span className="text-muted-foreground">(optional)</span></Label>
          <Input id="billing_email" type="email" placeholder="billing@acme.com" {...register('billing_email')} />
          {errors.billing_email && <p className="text-xs text-destructive">{errors.billing_email.message}</p>}
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="submit" isLoading={isSubmitting} className="flex-1">Create organization</Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
        </div>
      </form>
    </div>
  );
}

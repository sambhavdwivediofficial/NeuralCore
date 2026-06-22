// frontend/app/onboarding/page.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Building2, ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { onboardingSchema } from '@/lib/validators';
import { createOrganization } from '@/services/organizations';
import { useAuthContext } from '@/context/AuthContext';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

export default function OnboardingPage() {
  const { updateUser, refresh } = useAuthContext();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(onboardingSchema),
    defaultValues: { organization_name: '', billing_email: '' },
  });

  const onSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      const payload = { name: values.organization_name };
      if (values.billing_email) payload.billing_email = values.billing_email;
      await createOrganization(payload);
      await refresh();
      router.push(ROUTES.DASHBOARD);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-4 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Sparkles className="h-6 w-6" />
          </div>
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              Set up your workspace
            </h1>
            <p className="text-sm text-muted-foreground">
              Create an organization to start using NeuralCore
            </p>
          </div>
        </div>

        <div className="card-surface p-6">
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="organization_name">Organization name</Label>
              <div className="relative">
                <Input
                  id="organization_name"
                  type="text"
                  placeholder="Acme Inc."
                  className="pl-9"
                  {...register('organization_name')}
                />
                <Building2 className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              </div>
              {errors.organization_name && (
                <p className="text-xs text-destructive">{errors.organization_name.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="billing_email">
                Billing email{' '}
                <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="billing_email"
                type="email"
                placeholder="billing@company.com"
                {...register('billing_email')}
              />
              {errors.billing_email && (
                <p className="text-xs text-destructive">{errors.billing_email.message}</p>
              )}
            </div>

            <Button type="submit" isLoading={isSubmitting} className="w-full">
              Create workspace <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Your 14-day free trial starts automatically.
        </p>
      </div>
    </div>
  );
}

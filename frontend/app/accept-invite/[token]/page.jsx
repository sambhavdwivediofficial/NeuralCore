// frontend/app/accept-invite/[token]/page.jsx

'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Building2, UserCheck, AlertCircle } from 'lucide-react';
import { AuthCard } from '@/components/auth/AuthCard';
import { PasswordStrengthMeter } from '@/components/auth/PasswordStrengthMeter';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { PageLoader as Loader } from '@/components/common/Loader';
import { acceptInviteSchema } from '@/lib/validators';
import { useAuth } from '@/hooks/useAuth';
import { getInvite } from '@/services/auth';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export default function AcceptInvitePage() {
  const { token } = useParams();
  const { acceptInvite, isLoading } = useAuth();
  const [invite, setInvite] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm({
    resolver: zodResolver(acceptInviteSchema),
    defaultValues: { name: '', password: '', confirmPassword: '' },
  });

  const password = watch('password');

  useEffect(() => {
    getInvite(token)
      .then(setInvite)
      .catch((err) => setFetchError(getErrorMessage(err)))
      .finally(() => setFetchLoading(false));
  }, [token]);

  const onSubmit = async (values) => {
    try {
      await acceptInvite(token, { name: values.name, password: values.password });
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  if (fetchLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader size="lg" />
      </div>
    );
  }

  if (fetchError) {
    return (
      <AuthCard title="Invalid invitation">
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertCircle className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted-foreground">{fetchError}</p>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Accept your invitation"
      subtitle={`Join ${invite?.organization_name} on NeuralCore`}
    >
      <div className="flex flex-col gap-3 rounded-md border border-border bg-muted/40 p-3">
        <div className="flex items-center gap-2.5">
          <Building2 className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground">Organization</span>
            <span className="text-sm font-medium">{invite?.organization_name}</span>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <UserCheck className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground">Invited by</span>
            <span className="text-sm font-medium">{invite?.inviter_name}</span>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name">Your name</Label>
          <Input id="name" type="text" autoComplete="name" placeholder="Sambhav Dwivedi" {...register('name')} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" value={invite?.email ?? ''} disabled className="opacity-60" readOnly />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password">Create password</Label>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="••••••••"
              className="pr-9"
              {...register('password')}
            />
            <button type="button" onClick={() => setShowPassword((p) => !p)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground">
              {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          <PasswordStrengthMeter password={password} />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="confirmPassword">Confirm password</Label>
          <div className="relative">
            <Input
              id="confirmPassword"
              type={showConfirm ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="••••••••"
              className="pr-9"
              {...register('confirmPassword')}
            />
            <button type="button" onClick={() => setShowConfirm((p) => !p)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground">
              {showConfirm ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          {errors.confirmPassword && <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>}
        </div>

        <Button type="submit" isLoading={isLoading} className="w-full">
          Join {invite?.organization_name}
        </Button>
      </form>
    </AuthCard>
  );
}

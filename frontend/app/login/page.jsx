// app/login/page.jsx

'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Sparkles, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { Checkbox } from '@/components/common/Checkbox';
import { loginSchema } from '@/lib/validators';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signIn } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', remember: true },
  });

  const onSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      await signIn(values);
      const redirect = searchParams.get('redirect') || ROUTES.DASHBOARD;
      router.push(redirect);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="flex flex-col items-center gap-1 text-center">
            <h1 className="text-lg font-semibold tracking-tight text-foreground">
              Sign in to NeuralCore
            </h1>
            <p className="text-sm text-muted-foreground">
              Enterprise AI infrastructure platform
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="card-surface flex flex-col gap-4 p-6">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              {...register('email')}
            />
            {errors.email ? (
              <p className="text-xs text-destructive">{errors.email.message}</p>
            ) : null}
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <a href="#" className="text-xs text-primary hover:underline">
                Forgot password?
              </a>
            </div>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="••••••••"
                className="pr-9"
                {...register('password')}
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
              >
                {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
            {errors.password ? (
              <p className="text-xs text-destructive">{errors.password.message}</p>
            ) : null}
          </div>

          <div className="flex items-center gap-2">
            <Checkbox id="remember" {...register('remember')} defaultChecked />
            <Label htmlFor="remember" className="cursor-pointer font-normal text-muted-foreground">
              Stay signed in for 30 days
            </Label>
          </div>

          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Sign in
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Need access? Contact your workspace administrator.
        </p>
      </div>
    </div>
  );
}

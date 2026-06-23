// frontend/app/login/page.jsx

'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, ArrowRight, Sparkles, Activity, Brain, Zap } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { OAuthButtons } from '@/components/auth/OAuthButtons';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { Checkbox } from '@/components/common/Checkbox';
import { loginSchema } from '@/lib/validators';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';
import { Copyright } from 'lucide-react';

const ACTIVITY = [
  { icon: Brain, label: 'ResearchAgent completed task', time: '2s ago', color: 'text-violet-400' },
  { icon: Zap, label: 'Hybrid RAG — 312ms', time: '8s ago', color: 'text-primary' },
  { icon: Activity, label: '6 sources retrieved & reranked', time: '14s ago', color: 'text-emerald-400' },
  { icon: Brain, label: 'Memory layer updated', time: '31s ago', color: 'text-orange-400' },
];

export default function LoginPage() {
  const { signIn, isLoading } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', remember: true },
  });

  const onSubmit = async (values) => {
    try {
      await signIn(values);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      <div className="hidden lg:flex lg:w-[52%] xl:w-[42%] flex-col justify-between p-12 relative overflow-hidden border-r border-border bg-[hsl(240_10%_4%)]">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle at 20% 50%, hsl(var(--primary) / 0.07) 0%, transparent 50%), radial-gradient(circle at 80% 20%, hsl(280 65% 60% / 0.05) 0%, transparent 40%)',
          }}
        />
        <div
          className="absolute inset-0 pointer-events-none opacity-30"
          style={{
            backgroundImage: 'linear-gradient(hsl(var(--border) / 0.15) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border) / 0.15) 1px, transparent 1px)',
            backgroundSize: '4rem 4rem',
          }}
        />

        <Link href="/" className="relative flex items-center gap-2.5 w-fit">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight text-white">NeuralCore</span>
        </Link>

        <div className="relative flex flex-col gap-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="flex flex-col gap-3"
          >
            <h2 className="text-3xl font-bold tracking-tight text-white leading-tight">
              Your AI platform
              <br />
              is waiting.
            </h2>
            <p className="text-sm text-white/40 leading-relaxed max-w-xs">
              Agents are running, pipelines are processing, knowledge graphs are growing.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex flex-col gap-2.5 max-w-xs"
          >
            <span className="text-[0.625rem] uppercase tracking-widest text-white/25 font-medium mb-1">Live activity</span>
            {ACTIVITY.map((item, i) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.55 + i * 0.1 }}
                className="flex items-center gap-3 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5"
              >
                <item.icon className={`h-3.5 w-3.5 flex-shrink-0 ${item.color}`} />
                <span className="flex-1 text-xs text-white/60 truncate">{item.label}</span>
                <span className="text-[0.625rem] text-white/25 flex-shrink-0 font-mono">{item.time}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>

        <p className="text-xs text-muted-foreground flex items-center gap-1">
          <Copyright className="h-3 w-3" />
          {new Date().getFullYear()} NeuralCore. Built and Maintained by{' '}
          <a
            href="https://www.sambhavdwivedi.in"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline font-medium"
          >
            Sambhav Dwivedi
          </a>
        </p>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-12 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="w-full max-w-[340px]"
        >
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-semibold text-foreground">NeuralCore</span>
          </div>

          <div className="flex flex-col gap-1 mb-8">
            <h1 className="text-[1.375rem] font-bold tracking-tight text-foreground">Sign in</h1>
            <p className="text-sm text-muted-foreground">
              New here?{' '}
              <Link href={ROUTES.SIGNUP} className="text-foreground font-medium hover:underline underline-offset-4">
                Create an account
              </Link>
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email" className="text-xs font-medium">Email address</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                autoFocus
                placeholder="you@company.com"
                className="h-9 text-sm"
                {...register('email')}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-xs font-medium">Password</Label>
                <Link
                  href={ROUTES.FORGOT_PASSWORD}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-4"
                >
                  Forgot?
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="h-9 text-sm pr-9"
                  {...register('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  tabIndex={-1}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword
                    ? <EyeOff className="h-3.5 w-3.5" />
                    : <Eye className="h-3.5 w-3.5" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            <div className="flex items-center gap-2 py-0.5">
              <Checkbox id="remember" {...register('remember')} defaultChecked />
              <Label htmlFor="remember" className="cursor-pointer text-xs font-normal text-muted-foreground">
                Stay signed in for 30 days
              </Label>
            </div>

            <Button
              type="submit"
              isLoading={isLoading}
              className="w-full h-9 text-sm font-semibold gap-1.5 mt-0.5"
            >
              Continue <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </form>

          <div className="mt-5">
            <OAuthButtons action="Sign in" />
          </div>
        </motion.div>
      </div>
    </div>
  );
}

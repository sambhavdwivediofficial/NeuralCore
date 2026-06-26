// frontend/app/verify-email/page.jsx

'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { CheckCircle2, XCircle, Mail } from 'lucide-react';
import Link from 'next/link';
import { AuthCard } from '@/components/auth/AuthCard';
import { Button } from '@/components/common/Button';
import { PageLoader as Loader } from '@/components/common/Loader';
import { useAuth } from '@/hooks/useAuth';
import { requestVerifyEmail } from '@/services/auth';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const { verifyEmail, isLoading } = useAuth();
  const [status, setStatus] = useState('idle');
  const [resending, setResending] = useState(false);
  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) return;
    setStatus('verifying');
    verifyEmail(token)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'));
  }, [token, verifyEmail]);

  const handleResend = async () => {
    setResending(true);
    try {
      await requestVerifyEmail();
      toast.success('Verification email sent');
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setResending(false);
    }
  };

  if (status === 'verifying') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader size="lg" />
      </div>
    );
  }

  if (status === 'success') {
    return (
      <AuthCard title="Email verified">
        <div className="flex flex-col items-center gap-4 py-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-success/10 text-success">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted-foreground">
            Your email has been verified successfully.
          </p>
          <Link href={ROUTES.DASHBOARD} className="w-full">
            <Button className="w-full">Go to dashboard</Button>
          </Link>
        </div>
      </AuthCard>
    );
  }

  if (status === 'error') {
    return (
      <AuthCard title="Verification failed">
        <div className="flex flex-col items-center gap-4 py-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <XCircle className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted-foreground">
            This link is invalid or has expired.
          </p>
          <Button variant="outline" className="w-full" isLoading={resending} onClick={handleResend}>
            <Mail className="h-3.5 w-3.5" /> Resend verification email
          </Button>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Verify your email"
      subtitle="We sent a verification link to your email address"
    >
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Mail className="h-6 w-6" />
        </div>
        <p className="text-sm text-muted-foreground">
          Click the link in your email to verify your account. Check your spam folder if you don&apos;t see it.
        </p>
        <Button variant="outline" className="w-full" isLoading={resending} onClick={handleResend}>
          Resend verification email
        </Button>
      </div>
    </AuthCard>
  );
}


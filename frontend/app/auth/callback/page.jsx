// frontend/app/auth/callback/page.jsx

'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { CheckCircle2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { PageLoader as Loader } from '@/components/common/Loader';
import { Button } from '@/components/common/Button';
import { useAuthContext } from '@/context/AuthContext';
import { ROUTES } from '@/lib/routes';

export default function AuthCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refresh } = useAuthContext();
  const handled = useRef(false);

  const status = searchParams.get('status');
  const message = searchParams.get('message');

  useEffect(() => {
    if (handled.current || status !== 'success') return;
    handled.current = true;

    refresh().then((user) => {
      const dest = user?.tenant_id ? ROUTES.DASHBOARD : ROUTES.ONBOARDING;
      router.replace(dest);
    }).catch(() => {
      router.replace(ROUTES.DASHBOARD);
    });
  }, [status, refresh, router]);

  if (status === 'error') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <XCircle className="h-7 w-7" />
        </div>
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-base font-semibold text-foreground">Authentication failed</h1>
          <p className="max-w-xs text-sm text-muted-foreground">
            {message ?? 'Something went wrong during sign in. Please try again.'}
          </p>
        </div>
        <Link href={ROUTES.LOGIN}>
          <Button variant="outline">Back to sign in</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <Loader size="lg" />
      <p className="text-sm text-muted-foreground">Completing sign in…</p>
    </div>
  );
}


// frontend/app/login/mfa.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck } from 'lucide-react';
import { AuthCard } from '@/components/auth/AuthCard';
import { MfaCodeInput } from '@/components/auth/MfaCodeInput';
import { Button } from '@/components/common/Button';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';
import { ROUTES } from '@/lib/routes';

export default function MfaPage() {
  const { completeMfa, mfaPending, isLoading } = useAuth();
  const router = useRouter();
  const [code, setCode] = useState('');

  if (!mfaPending) {
    if (typeof window !== 'undefined') router.replace(ROUTES.LOGIN);
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (code.length !== 6) {
      toast.error('Enter the 6-digit code from your authenticator app');
      return;
    }
    try {
      await completeMfa(code);
    } catch (error) {
      toast.error(getErrorMessage(error));
      setCode('');
    }
  };

  return (
    <AuthCard
      title="Two-factor authentication"
      subtitle="Enter the code from your authenticator app"
      footer={
        <button
          type="button"
          onClick={() => router.push(ROUTES.LOGIN)}
          className="text-primary hover:underline"
        >
          Back to sign in
        </button>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="flex justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <ShieldCheck className="h-6 w-6" />
          </div>
        </div>

        <MfaCodeInput value={code} onChange={setCode} disabled={isLoading} />

        <Button
          type="submit"
          isLoading={isLoading}
          disabled={code.length !== 6}
          className="w-full"
        >
          Verify
        </Button>
      </form>
    </AuthCard>
  );
}

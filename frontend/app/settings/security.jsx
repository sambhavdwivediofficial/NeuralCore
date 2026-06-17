// app/settings/security.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, ShieldCheck, Monitor, LogOut } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { Switch } from '@/components/common/Switch';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from '@/components/common/Card';
import { Separator } from '@/components/common/Separator';
import { EmptyState } from '@/components/common/EmptyState';
import { useSessions } from '@/hooks/useAuth';
import { changePassword, toggleTwoFactor, revokeSession } from '@/services/auth';
import { securitySettingsSchema } from '@/lib/validators';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/utils';

export default function SecuritySettingsPage() {
  const router = useRouter();
  const { sessions, isLoading, refresh } = useSessions();
  const [isSaving, setIsSaving] = useState(false);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [isTogglingTwoFactor, setIsTogglingTwoFactor] = useState(false);
  const [revokingId, setRevokingId] = useState(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ resolver: zodResolver(securitySettingsSchema) });

  const onSubmit = async (values) => {
    setIsSaving(true);
    try {
      await changePassword({
        current_password: values.currentPassword,
        new_password: values.newPassword,
      });
      toast.success('Password updated');
      reset();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleTwoFactor = async (enabled) => {
    setIsTogglingTwoFactor(true);
    try {
      await toggleTwoFactor(enabled);
      setTwoFactorEnabled(enabled);
      toast.success(
        enabled ? 'Two-factor authentication enabled' : 'Two-factor authentication disabled'
      );
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsTogglingTwoFactor(false);
    }
  };

  const handleRevokeSession = async (session) => {
    setRevokingId(session.id);
    try {
      await revokeSession(session.id);
      toast.success('Session revoked');
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.SETTINGS)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Settings
        </Button>

        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Security</h1>
          <p className="text-sm text-muted-foreground">
            Manage your password, two-factor authentication, and active sessions
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Change password</CardTitle>
            <CardDescription>Choose a strong password you don&apos;t use elsewhere</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="current-password">Current password</Label>
                <Input id="current-password" type="password" {...register('currentPassword')} />
                {errors.currentPassword ? (
                  <p className="text-xs text-destructive">{errors.currentPassword.message}</p>
                ) : null}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="new-password">New password</Label>
                <Input id="new-password" type="password" {...register('newPassword')} />
                {errors.newPassword ? (
                  <p className="text-xs text-destructive">{errors.newPassword.message}</p>
                ) : null}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="confirm-password">Confirm new password</Label>
                <Input id="confirm-password" type="password" {...register('confirmPassword')} />
                {errors.confirmPassword ? (
                  <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
                ) : null}
              </div>
              <div className="flex justify-end pt-2">
                <Button type="submit" isLoading={isSaving}>
                  Update password
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Two-factor authentication</CardTitle>
            <CardDescription>Add an extra layer of security to your account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">
                  {twoFactorEnabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <Switch
                checked={twoFactorEnabled}
                onCheckedChange={handleToggleTwoFactor}
                disabled={isTogglingTwoFactor}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active sessions</CardTitle>
            <CardDescription>Devices currently signed in to your account</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex flex-col gap-2 p-4">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="skeleton h-12 w-full rounded-md" />
                ))}
              </div>
            ) : sessions.length === 0 ? (
              <div className="p-4">
                <EmptyState icon={Monitor} title="No active sessions" />
              </div>
            ) : (
              <div className="flex flex-col divide-y divide-border">
                {sessions.map((session) => (
                  <div key={session.id} className="flex items-center justify-between p-4">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm text-foreground">
                        {session.device} · {session.location || 'Unknown location'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        Last active {formatRelativeTime(session.last_active_at)}
                      </span>
                    </div>
                    {session.is_current ? (
                      <span className="text-xs font-medium text-success">This device</span>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        isLoading={revokingId === session.id}
                        onClick={() => handleRevokeSession(session)}
                      >
                        <LogOut className="h-3.5 w-3.5" />
                        Revoke
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
          <Separator />
          <CardFooter className="justify-end pt-4">
            <Button variant="outline" size="sm">
              Sign out all other sessions
            </Button>
          </CardFooter>
        </Card>
      </div>
    </AppShell>
  );
}

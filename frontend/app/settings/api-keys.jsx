// app/settings/api-keys.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, KeyRound, Plus, Copy, Trash2, Eye, EyeOff } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { Card, CardContent } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonText } from '@/components/common/Loader';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from '@/components/common/Modal';
import { useApiKeys } from '@/hooks/useAuth';
import { createApiKey, revokeApiKey } from '@/services/auth';
import { apiKeySchema } from '@/lib/validators';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/utils';

const SCOPES = ['read', 'write', 'admin'];

export default function ApiKeysPage() {
  const router = useRouter();
  const { apiKeys, isLoading, refresh } = useApiKeys();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState(null);
  const [newKeySecret, setNewKeySecret] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [visibleKeyId, setVisibleKeyId] = useState(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(apiKeySchema),
    defaultValues: { name: '', scope: 'read' },
  });

  const handleCreate = async (values) => {
    setIsSubmitting(true);
    try {
      const result = await createApiKey({ name: values.name, scope: values.scope });
      setNewKeySecret(result.secret);
      reset();
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevoke = async () => {
    if (!revokeTarget) return;
    setIsRevoking(true);
    try {
      await revokeApiKey(revokeTarget.id);
      toast.success(`${revokeTarget.name} revoked`);
      setRevokeTarget(null);
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsRevoking(false);
    }
  };

  const copyToClipboard = (value) => {
    navigator.clipboard.writeText(value);
    toast.success('Copied to clipboard');
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

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">API keys</h1>
            <p className="text-sm text-muted-foreground">
              Generate keys for programmatic access to the NeuralCore API
            </p>
          </div>
          <Button
            onClick={() => {
              setNewKeySecret(null);
              setShowCreateModal(true);
            }}
          >
            <Plus className="h-3.5 w-3.5" />
            New key
          </Button>
        </div>

        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-4">
                <SkeletonText lines={4} />
              </div>
            ) : apiKeys.length === 0 ? (
              <div className="p-4">
                <EmptyState
                  icon={KeyRound}
                  title="No API keys"
                  description="Create a key to authenticate requests to the NeuralCore API."
                />
              </div>
            ) : (
              <div className="flex flex-col divide-y divide-border">
                {apiKeys.map((key) => (
                  <div key={key.id} className="flex items-center justify-between p-4">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{key.name}</span>
                        <Badge variant="muted" className="capitalize">
                          {key.scope}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                        <span>
                          {visibleKeyId === key.id ? `${key.prefix}••••••••••••` : '••••••••••••••••'}
                        </span>
                        <button
                          onClick={() => setVisibleKeyId(visibleKeyId === key.id ? null : key.id)}
                        >
                          {visibleKeyId === key.id ? (
                            <EyeOff className="h-3 w-3" />
                          ) : (
                            <Eye className="h-3 w-3" />
                          )}
                        </button>
                      </div>
                      <span className="text-2xs text-muted-foreground">
                        Created {formatRelativeTime(key.created_at)}
                        {key.last_used_at ? ` · Last used ${formatRelativeTime(key.last_used_at)}` : ''}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="iconSm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setRevokeTarget(key)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Modal
        open={showCreateModal}
        onOpenChange={(open) => {
          setShowCreateModal(open);
          if (!open) setNewKeySecret(null);
        }}
      >
        <ModalContent>
          {newKeySecret ? (
            <>
              <ModalHeader>
                <ModalTitle>API key created</ModalTitle>
                <ModalDescription>
                  Copy this key now. For security reasons it will not be shown again.
                </ModalDescription>
              </ModalHeader>
              <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3">
                <code className="flex-1 truncate text-xs text-foreground">{newKeySecret}</code>
                <Button variant="ghost" size="iconSm" onClick={() => copyToClipboard(newKeySecret)}>
                  <Copy className="h-3.5 w-3.5" />
                </Button>
              </div>
              <ModalFooter>
                <Button onClick={() => setShowCreateModal(false)}>Done</Button>
              </ModalFooter>
            </>
          ) : (
            <>
              <ModalHeader>
                <ModalTitle>Create API key</ModalTitle>
                <ModalDescription>Give your key a name and select a permission scope</ModalDescription>
              </ModalHeader>
              <form onSubmit={handleSubmit(handleCreate)} className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="key-name">Name</Label>
                  <Input id="key-name" placeholder="Production server" {...register('name')} />
                  {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Scope</Label>
                  <Select value={watch('scope')} onValueChange={(value) => setValue('scope', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SCOPES.map((scope) => (
                        <SelectItem key={scope} value={scope} className="capitalize">
                          {scope}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <ModalFooter>
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" isLoading={isSubmitting}>
                    Create key
                  </Button>
                </ModalFooter>
              </form>
            </>
          )}
        </ModalContent>
      </Modal>

      <Modal open={Boolean(revokeTarget)} onOpenChange={(open) => !open && setRevokeTarget(null)}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Revoke API key</ModalTitle>
            <ModalDescription>
              Any application using &quot;{revokeTarget?.name}&quot; will immediately lose access. This
              action cannot be undone.
            </ModalDescription>
          </ModalHeader>
          <ModalFooter>
            <Button variant="outline" onClick={() => setRevokeTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isRevoking} onClick={handleRevoke}>
              Revoke key
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}

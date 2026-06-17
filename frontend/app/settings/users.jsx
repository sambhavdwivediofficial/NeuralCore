// app/settings/users.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Users, Plus, MoreHorizontal, Trash2 } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Label } from '@/components/common/Label';
import { Avatar } from '@/components/common/Avatar';
import { Badge } from '@/components/common/Badge';
import { Card, CardContent } from '@/components/common/Card';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/common/DropdownMenu';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from '@/components/common/Modal';
import { useTeamMembers } from '@/hooks/useAuth';
import { inviteUser, updateUserRole, removeUser } from '@/services/auth';
import { inviteUserSchema } from '@/lib/validators';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { USER_ROLES, USER_ROLE_LABELS } from '@/lib/constants';
import { formatRelativeTime } from '@/lib/utils';

export default function TeamMembersPage() {
  const router = useRouter();
  const { members, isLoading, refresh } = useTeamMembers();
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [removeTarget, setRemoveTarget] = useState(null);
  const [isInviting, setIsInviting] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);
  const [updatingRoleId, setUpdatingRoleId] = useState(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(inviteUserSchema),
    defaultValues: { email: '', role: USER_ROLES.MEMBER },
  });

  const handleInvite = async (values) => {
    setIsInviting(true);
    try {
      await inviteUser({ email: values.email, role: values.role });
      toast.success(`Invitation sent to ${values.email}`);
      reset();
      setShowInviteModal(false);
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsInviting(false);
    }
  };

  const handleRoleChange = async (member, role) => {
    setUpdatingRoleId(member.id);
    try {
      await updateUserRole(member.id, role);
      toast.success(`${member.name}'s role updated`);
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setUpdatingRoleId(null);
    }
  };

  const handleRemove = async () => {
    if (!removeTarget) return;
    setIsRemoving(true);
    try {
      await removeUser(removeTarget.id);
      toast.success(`${removeTarget.name} removed`);
      setRemoveTarget(null);
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsRemoving(false);
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

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Team</h1>
            <p className="text-sm text-muted-foreground">
              Manage who has access to this NeuralCore workspace
            </p>
          </div>
          <Button onClick={() => setShowInviteModal(true)}>
            <Plus className="h-3.5 w-3.5" />
            Invite member
          </Button>
        </div>

        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-4">
                <SkeletonText lines={5} />
              </div>
            ) : members.length === 0 ? (
              <div className="p-4">
                <EmptyState
                  icon={Users}
                  title="No team members"
                  description="Invite teammates to collaborate on this workspace."
                />
              </div>
            ) : (
              <div className="flex flex-col divide-y divide-border">
                {members.map((member) => (
                  <div key={member.id} className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <Avatar name={member.name} src={member.avatar_url} />
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-foreground">{member.name}</span>
                        <span className="text-xs text-muted-foreground">{member.email}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {member.status === 'pending' ? (
                        <Badge variant="muted">Pending</Badge>
                      ) : (
                        <span className="text-2xs text-muted-foreground">
                          Joined {formatRelativeTime(member.joined_at)}
                        </span>
                      )}
                      <Select
                        value={member.role}
                        onValueChange={(role) => handleRoleChange(member, role)}
                        disabled={updatingRoleId === member.id}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.values(USER_ROLES).map((role) => (
                            <SelectItem key={role} value={role}>
                              {USER_ROLE_LABELS[role]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="iconSm">
                            <MoreHorizontal className="h-3.5 w-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setRemoveTarget(member)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Modal open={showInviteModal} onOpenChange={setShowInviteModal}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Invite a team member</ModalTitle>
            <ModalDescription>
              They will receive an email invitation to join this workspace
            </ModalDescription>
          </ModalHeader>
          <form onSubmit={handleSubmit(handleInvite)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="invite-email">Email address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="teammate@company.com"
                {...register('email')}
              />
              {errors.email ? <p className="text-xs text-destructive">{errors.email.message}</p> : null}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Role</Label>
              <Select value={watch('role')} onValueChange={(value) => setValue('role', value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(USER_ROLES).map((role) => (
                    <SelectItem key={role} value={role}>
                      {USER_ROLE_LABELS[role]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <ModalFooter>
              <Button type="button" variant="outline" onClick={() => setShowInviteModal(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isInviting}>
                Send invite
              </Button>
            </ModalFooter>
          </form>
        </ModalContent>
      </Modal>

      <Modal open={Boolean(removeTarget)} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Remove team member</ModalTitle>
            <ModalDescription>
              &quot;{removeTarget?.name}&quot; will immediately lose access to this workspace.
            </ModalDescription>
          </ModalHeader>
          <ModalFooter>
            <Button variant="outline" onClick={() => setRemoveTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isRemoving} onClick={handleRemove}>
              Remove
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}

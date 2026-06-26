// frontend/app/organizations/[org_id]/page.jsx

'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Settings, Users, FolderKanban, Bot, BookOpen, ArrowLeft } from 'lucide-react';
import { PageLoader as Loader } from '@/components/common/Loader';
import { useOrganization } from '@/hooks/useOrganizations';
import { useAuthContext } from '@/context/AuthContext';
import { ROUTES } from '@/lib/routes';
import { cn } from '@/lib/utils';

function StatTile({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
      <div className={cn('flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md', color)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex flex-col">
        <span className="text-lg font-bold font-mono tracking-tight text-foreground">{value ?? '—'}</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
    </div>
  );
}

const PLAN_STYLES = {
  free: 'bg-muted text-muted-foreground',
  pro: 'bg-primary/10 text-primary border border-primary/20',
  enterprise: 'bg-warning/10 text-warning border border-warning/20',
  trial: 'bg-success/10 text-success border border-success/20',
};

export default function OrganizationDetailPage() {
  const { org_id } = useParams();
  const { organization, isLoading, error } = useOrganization(org_id);
  const { user } = useAuthContext();

  const canManage = ['super_admin', 'owner', 'admin'].includes(user?.role);

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (error || !organization) return <div className="p-6 text-sm text-muted-foreground">Organization not found.</div>;

  const plan = organization.plan ?? 'free';

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <Link href={ROUTES.ORGANIZATIONS}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex flex-col">
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-semibold text-foreground">{organization.name}</h1>
            <span className={cn('text-[0.6875rem] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full', PLAN_STYLES[plan])}>
              {plan}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{organization.slug ?? organization.id}</p>
        </div>
        {canManage && (
          <Link href={ROUTES.ORGANIZATION_SETTINGS(org_id)} className="ml-auto flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors">
            <Settings className="h-3.5 w-3.5" /> Settings
          </Link>
        )}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile icon={Users} label="Members" value={organization.member_count} color="text-blue-500 bg-blue-500/10" />
        <StatTile icon={FolderKanban} label="Projects" value={organization.project_count} color="text-violet-500 bg-violet-500/10" />
        <StatTile icon={Bot} label="Agents" value={organization.agent_count} color="text-emerald-500 bg-emerald-500/10" />
        <StatTile icon={BookOpen} label="Knowledge Bases" value={organization.kb_count} color="text-orange-500 bg-orange-500/10" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-surface p-5 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-foreground">Organization details</h2>
          <div className="grid grid-cols-[7rem_1fr] gap-y-3 gap-x-4 text-xs">
            {[
              { key: 'ID', val: organization.id },
              { key: 'Name', val: organization.name },
              { key: 'Plan', val: plan },
              { key: 'Billing email', val: organization.billing_email ?? '—' },
              { key: 'Status', val: organization.status ?? 'active' },
              { key: 'Created', val: organization.created_at ? new Date(organization.created_at).toLocaleDateString() : '—' },
            ].map(({ key, val }) => (
              <>
                <span key={`k-${key}`} className="text-muted-foreground font-mono">{key}</span>
                <span key={`v-${key}`} className="text-foreground break-all">{val}</span>
              </>
            ))}
          </div>
        </div>

        <div className="card-surface p-5 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-foreground">Quick actions</h2>
          <div className="flex flex-col gap-2">
            {[
              { label: 'Manage projects', href: ROUTES.PROJECTS, icon: FolderKanban },
              { label: 'View agents', href: ROUTES.AGENTS, icon: Bot },
              { label: 'Knowledge bases', href: ROUTES.KNOWLEDGE_BASES, icon: BookOpen },
              { label: 'Team members', href: ROUTES.SETTINGS_USERS, icon: Users },
            ].map(({ label, href, icon: Icon }) => (
              <Link key={label} href={href}
                className="flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                <Icon className="h-3.5 w-3.5" /> {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

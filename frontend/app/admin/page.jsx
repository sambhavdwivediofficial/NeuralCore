// frontend/app/admin/page.jsx

'use client';

import Link from 'next/link';
import { ShieldAlert, Building2, Users, Bot, Activity, ArrowRight } from 'lucide-react';
import { PlatformStats } from '@/components/admin/PlatformStats';
import { PageLoader as Loader } from '@/components/common/Loader';
import { useAdminStats } from '@/hooks/useAdmin';
import { useAuthContext } from '@/context/AuthContext';
import { ROUTES } from '@/lib/routes';

export default function AdminPage() {
  const { stats, isLoading } = useAdminStats();
  const { user } = useAuthContext();

  if (user?.role !== 'super_admin') {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-8 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <ShieldAlert className="h-7 w-7" />
        </div>
        <div className="flex flex-col gap-1.5">
          <h3 className="text-sm font-semibold text-foreground">Access restricted</h3>
          <p className="text-xs text-muted-foreground">Admin panel is only accessible to super_admin accounts.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-warning" />
            <h1 className="text-lg font-semibold text-foreground">Admin Panel</h1>
          </div>
          <p className="text-xs text-muted-foreground">Platform-wide visibility — super_admin only</p>
        </div>
        <Link href={ROUTES.ADMIN_ORGANIZATIONS}
          className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors">
          <Building2 className="h-3.5 w-3.5" /> All orgs <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      <PlatformStats stats={stats} isLoading={isLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-surface p-5 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-foreground">Platform health</h2>
          <div className="flex flex-col gap-2.5">
            {[
              { label: 'API server', status: 'healthy' },
              { label: 'PostgreSQL', status: 'healthy' },
              { label: 'Redis cache', status: 'healthy' },
              { label: 'Qdrant (vector)', status: 'healthy' },
              { label: 'Celery workers', status: 'healthy' },
            ].map(({ label, status }) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{label}</span>
                <div className="flex items-center gap-1.5">
                  <div className="h-1.5 w-1.5 rounded-full bg-success" />
                  <span className="text-success font-medium capitalize">{status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card-surface p-5 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-foreground">Quick links</h2>
          <div className="flex flex-col gap-1">
            {[
              { label: 'All organizations', href: ROUTES.ADMIN_ORGANIZATIONS, icon: Building2 },
              { label: 'Monitoring & alerts', href: ROUTES.MONITORING_ALERTS, icon: Activity },
              { label: 'System logs', href: ROUTES.MONITORING_LOGS, icon: Activity },
              { label: 'Team management', href: ROUTES.SETTINGS_USERS, icon: Users },
              { label: 'Agent overview', href: ROUTES.AGENTS, icon: Bot },
            ].map(({ label, href, icon: Icon }) => (
              <Link key={label} href={href}
                className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                <Icon className="h-3.5 w-3.5" /> {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}


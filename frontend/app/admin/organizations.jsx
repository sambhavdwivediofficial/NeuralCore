// frontend/app/admin/organizations.jsx

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Building2, Users, Calendar, Search } from 'lucide-react';
import { PageLoader as Loader } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { SearchBar } from '@/components/common/SearchBar';
import { useAdminOrganizations } from '@/hooks/useAdmin';
import { ROUTES } from '@/lib/routes';
import { cn } from '@/lib/utils';

const PLAN_STYLES = {
  free: 'text-muted-foreground bg-muted',
  pro: 'text-primary bg-primary/10',
  enterprise: 'text-warning bg-warning/10',
  trial: 'text-success bg-success/10',
};

export default function AdminOrganizationsPage() {
  const { organizations, isLoading, error } = useAdminOrganizations();
  const [search, setSearch] = useState('');

  const filtered = organizations.filter((o) =>
    o.name?.toLowerCase().includes(search.toLowerCase()) ||
    o.billing_email?.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href={ROUTES.ADMIN}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex flex-col gap-0.5">
            <h1 className="text-lg font-semibold text-foreground">All Organizations</h1>
            <p className="text-xs text-muted-foreground">{organizations.length} organizations on platform</p>
          </div>
        </div>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by name or email…" className="w-64" />
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={Building2} title="No organizations found" description="Try a different search term." />
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Organization</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground hidden sm:table-cell">Plan</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground hidden md:table-cell">Members</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground hidden lg:table-cell">Created</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((org, i) => {
                const plan = org.plan ?? 'free';
                return (
                  <tr key={org.id}
                    className={cn('border-b border-border last:border-0 hover:bg-muted/30 transition-colors', i % 2 === 0 ? '' : 'bg-muted/10')}>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-0.5">
                        <Link href={ROUTES.ORGANIZATION(org.id)}
                          className="font-medium text-foreground hover:text-primary transition-colors truncate max-w-[12rem]">
                          {org.name}
                        </Link>
                        {org.billing_email && (
                          <span className="text-muted-foreground truncate max-w-[12rem]">{org.billing_email}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className={cn('rounded-full px-2 py-0.5 font-medium uppercase tracking-wide text-[0.625rem]', PLAN_STYLES[plan])}>
                        {plan}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <Users className="h-3 w-3" />
                        {org.member_count ?? 0}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-muted-foreground">
                      {org.created_at ? new Date(org.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <div className={cn('h-1.5 w-1.5 rounded-full', org.status === 'active' ? 'bg-success' : 'bg-muted-foreground')} />
                        <span className="text-muted-foreground capitalize">{org.status ?? 'active'}</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


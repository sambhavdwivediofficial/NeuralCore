// frontend/app/organizations/page.jsx

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Building2, Plus } from 'lucide-react';
import { OrgCard } from '@/components/organizations/OrgCard';
import { EmptyState } from '@/components/common/EmptyState';
import { Loader } from '@/components/common/Loader';
import { SearchBar } from '@/components/common/SearchBar';
import { useOrganizations } from '@/hooks/useOrganizations';
import { useOrganizationContext } from '@/context/OrganizationContext';
import { ROUTES } from '@/lib/routes';

export default function OrganizationsPage() {
  const { organizations, isLoading, error } = useOrganizations();
  const { activeOrg, switchOrg } = useOrganizationContext();
  const [search, setSearch] = useState('');

  const filtered = organizations.filter((o) =>
    o.name.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <div className="flex h-full items-center justify-center"><Loader size="lg" /></div>;
  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-lg font-semibold text-foreground">Organizations</h1>
          <p className="text-xs text-muted-foreground">{organizations.length} organization{organizations.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          <SearchBar value={search} onChange={setSearch} placeholder="Search…" className="w-48" />
          <Link href={ROUTES.ORGANIZATION_CREATE}
            className="flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
            <Plus className="h-3.5 w-3.5" /> New org
          </Link>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={Building2}
          title={search ? 'No organizations match' : 'No organizations yet'}
          description={search ? 'Try a different search.' : 'Create your first organization to get started.'}
          action={!search ? { label: 'Create organization', href: ROUTES.ORGANIZATION_CREATE } : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((org) => (
            <OrgCard
              key={org.id}
              org={org}
              isActive={activeOrg?.id === org.id}
              onClick={() => switchOrg(org)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

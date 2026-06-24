// frontend/components/organizations/OrgSwitcher.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Check, ChevronDown, Plus, Building2 } from 'lucide-react';
import { useOrganizationContext } from '@/context/OrganizationContext';
import { ROUTES } from '@/lib/routes';
import { cn } from '@/lib/utils';

export function OrgSwitcher({ collapsed = false }) {
  const { organizations, activeOrg, switchOrg } = useOrganizationContext();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const initials = (name = '') =>
    name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className={cn(
          'flex items-center gap-2 w-full rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent',
          open && 'bg-accent'
        )}
      >
        {activeOrg ? (
          <div className="org-avatar h-6 w-6 text-xs flex-shrink-0"
            style={{ minWidth: '1.5rem', minHeight: '1.5rem' }}>
            {initials(activeOrg.name)}
          </div>
        ) : (
          <Building2 className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        )}
        {!collapsed && (
          <>
            <span className="flex-1 text-left truncate font-medium text-foreground text-xs">
              {activeOrg?.name ?? 'Select org'}
            </span>
            <ChevronDown className={cn('h-3 w-3 text-muted-foreground transition-transform flex-shrink-0', open && 'rotate-180')} />
          </>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full mt-1 z-50 w-56 rounded-lg border border-border bg-popover shadow-lg py-1 overflow-hidden">
            <div className="px-2 py-1.5">
              <p className="text-[0.625rem] font-semibold uppercase tracking-wider text-muted-foreground px-1">
                Organizations
              </p>
            </div>

            {organizations.map((org) => (
              <button
                key={org.id}
                type="button"
                onClick={() => { switchOrg(org); setOpen(false); }}
                className="org-switcher-item"
                data-active={activeOrg?.id === org.id ? 'true' : 'false'}
              >
                <div className="org-avatar h-6 w-6 text-xs flex-shrink-0"
                  style={{ minWidth: '1.5rem', minHeight: '1.5rem' }}>
                  {initials(org.name)}
                </div>
                <span className="flex-1 truncate text-xs">{org.name}</span>
                {activeOrg?.id === org.id && (
                  <Check className="h-3 w-3 text-primary flex-shrink-0" />
                )}
              </button>
            ))}

            <div className="my-1 h-px bg-border mx-2" />
            <button
              type="button"
              onClick={() => { router.push(ROUTES.ORGANIZATION_CREATE); setOpen(false); }}
              className="org-switcher-item text-muted-foreground hover:text-foreground"
            >
              <div className="flex h-6 w-6 items-center justify-center rounded-md border border-dashed border-border flex-shrink-0">
                <Plus className="h-3 w-3" />
              </div>
              <span className="text-xs">New organization</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
}

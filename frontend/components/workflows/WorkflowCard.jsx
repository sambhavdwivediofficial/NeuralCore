// frontend/components/organizations/OrgCard.jsx

import Link from 'next/link';
import { Users, FolderKanban, Calendar, ArrowRight } from 'lucide-react';
import { ROUTES } from '@/lib/routes';
import { cn } from '@/lib/utils';

function OrgAvatar({ name, size = 'md' }) {
  const initials = (name ?? '?').split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2);
  const sizes = { sm: 'h-8 w-8 text-xs', md: 'h-10 w-10 text-sm', lg: 'h-12 w-12 text-base' };
  return (
    <div className={cn('org-avatar', sizes[size])}>
      {initials}
    </div>
  );
}

const PLAN_LABELS = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise', trial: 'Trial' };

export function OrgCard({ org, isActive = false, onClick }) {
  const plan = org.plan ?? 'free';

  return (
    <div
      className="org-card"
      data-active={isActive ? 'true' : 'false'}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <OrgAvatar name={org.name} size="md" />
          <div className="flex flex-col gap-0.5 min-w-0">
            <span className="text-sm font-semibold text-foreground truncate">{org.name}</span>
            <span className="text-xs text-muted-foreground truncate">{org.slug ?? org.id}</span>
          </div>
        </div>
        <span className="org-plan-badge flex-shrink-0" data-plan={plan}>
          {PLAN_LABELS[plan] ?? plan}
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Users className="h-3 w-3" />
          <span>{org.member_count ?? 0} members</span>
        </div>
        <div className="flex items-center gap-1.5">
          <FolderKanban className="h-3 w-3" />
          <span>{org.project_count ?? 0} projects</span>
        </div>
        {org.created_at && (
          <div className="flex items-center gap-1.5">
            <Calendar className="h-3 w-3" />
            <span>{new Date(org.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
          </div>
        )}
      </div>

      {!onClick && (
        <Link
          href={ROUTES.ORGANIZATION(org.id)}
          className="flex items-center gap-1 text-xs text-primary hover:underline w-fit"
          onClick={(e) => e.stopPropagation()}
        >
          View organization <ArrowRight className="h-3 w-3" />
        </Link>
      )}
    </div>
  );
}

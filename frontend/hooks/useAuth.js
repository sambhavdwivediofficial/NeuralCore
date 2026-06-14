// hooks/useAuth.js

import { useAuthContext } from '@/context/AuthContext';
import { hasPermission, hasAnyPermission, isRoleAtLeast } from '@/lib/permissions';

export function useAuth() {
  const context = useAuthContext();

  const can = (permission) => hasPermission(context.user?.role, permission);
  const canAny = (permissions) => hasAnyPermission(context.user?.role, permissions);
  const isAtLeast = (role) => isRoleAtLeast(context.user?.role, role);

  return {
    ...context,
    can,
    canAny,
    isAtLeast,
  };
}